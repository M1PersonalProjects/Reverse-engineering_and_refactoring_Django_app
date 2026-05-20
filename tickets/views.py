from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .forms import AttachmentForm, CommentForm, ProfileForm, SignupForm, TicketForm
from .models import Attachment, Profile, Ticket, RoleRequest


def ensure_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def index(request):
    if request.user.is_authenticated:
        return redirect('ticket_list')
    return redirect('login')


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Аккаунт создан')
            return redirect('ticket_list')
    else:
        form = SignupForm()
    return render(request, 'tickets/signup.html', {'form': form})


@login_required
def ticket_list(request):
    ensure_profile(request.user)

    qs = Ticket.objects.all().select_related('owner')

    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 5)
    page_number = request.GET.get('page', '1')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(paginator.num_pages)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'tickets/ticket_list.html', {'page_obj': page_obj, 'status': status})


@login_required
def ticket_search(request):
    q = request.GET.get('q', '').strip()
    results = []
    
    if q:
        results = Ticket.objects.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).order_by('-created_at')
        
    return render(request, 'tickets/search.html', {'q': q, 'results': results})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related('owner').prefetch_related('comments__author', 'attachments'),
        pk=pk,
    )

    if getattr(ticket, 'is_private', False):
        user_role = request.user.profile.role
        if ticket.owner != request.user and user_role not in [Profile.ROLE_ADMIN, 'moderator']:
            raise PermissionDenied("У вас нет прав для просмотра этой приватной заявки.")

    comment_form = CommentForm()
    attachment_form = AttachmentForm()
    return render(
        request,
        'tickets/ticket_detail.html',
        {'ticket': ticket, 'comment_form': comment_form, 'attachment_form': attachment_form},
    )


@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.owner = request.user
            ticket.save()
            messages.success(request, 'Заявка создана')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, 'tickets/ticket_form.html', {'form': form, 'mode': 'create'})


@login_required
def ticket_edit(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    user_role = request.user.profile.role
    if ticket.owner != request.user and user_role not in [Profile.ROLE_ADMIN, 'moderator']:
        raise PermissionDenied("У вас нет прав для редактирования этой заявки.")

    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, 'Заявка обновлена')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm(instance=ticket)
    return render(request, 'tickets/ticket_form.html', {'form': form, 'mode': 'edit', 'ticket': ticket})


@login_required
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    user_role = request.user.profile.role
    if ticket.owner != request.user and user_role not in [Profile.ROLE_ADMIN, 'moderator']:
        raise PermissionDenied("У вас нет прав для удаления этой заявки.")

    if request.method == 'POST':
        ticket.delete()
        messages.warning(request, 'Заявка удалена')
        return redirect('ticket_list')
    
    return render(request, 'tickets/ticket_confirm_delete.html', {'ticket': ticket})


@login_required
def comment_add(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method != 'POST':
        return redirect('ticket_detail', pk=pk)

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.save()
        messages.success(request, 'Комментарий добавлен')
    return redirect('ticket_detail', pk=pk)


@login_required
def attachment_upload(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if (
        ticket.is_private
        and ticket.owner != request.user
        and request.user.profile.role not in ['admin', 'moderator']
    ):
        messages.error(request, 'У вас нет прав для добавления файлов к этому тикету.')
        return redirect('ticket_detail', pk=ticket.pk)

    if request.method == 'POST':
        form = AttachmentForm(request.POST, request.FILES)

        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.ticket = ticket
            attachment.uploaded_by = request.user
            attachment.save()

            messages.success(request, 'Файл успешно прикреплен к заявке.')
            return redirect('ticket_detail', pk=ticket.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Ошибка загрузки: {error}')
    return redirect('ticket_detail', pk=ticket.pk)


@login_required
def attachment_download(request, attachment_id):
    attachment = get_object_or_404(Attachment.objects.select_related('ticket'), pk=attachment_id)
    try:
        return FileResponse(attachment.file.open('rb'), as_attachment=True, filename=attachment.original_name)
    except FileNotFoundError:
        raise Http404('Файл не найден')


@login_required
def profile_edit(request):
    profile = ensure_profile(request.user)
    
    role_requests = []
    if profile.role == Profile.ROLE_ADMIN:
        role_requests = RoleRequest.objects.filter(status=RoleRequest.STATUS_PENDING).select_related('user')

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            
            new_role = form.cleaned_data.get('requested_role')
            if new_role and new_role != profile.role:
                already_exists = RoleRequest.objects.filter(
                    user=request.user, 
                    requested_role=new_role, 
                    status=RoleRequest.STATUS_PENDING
                ).exists()
                
                if not already_exists:
                    RoleRequest.objects.create(user=request.user, requested_role=new_role)
                    messages.info(request, 'Заявка на смену роли отправлена администратору.')
                else:
                    messages.warning(request, 'Вы уже отправили заявку на эту роль.')
            
            messages.success(request, 'Профиль успешно обновлен.')
            return redirect('profile_edit')
    else:
        form = ProfileForm(instance=profile)
        
    return render(request, 'tickets/profile.html', {
        'form': form, 
        'profile': profile,
        'role_requests': role_requests
    })


@login_required
def admin_console(request):
    profile = ensure_profile(request.user)
    if profile.role != Profile.ROLE_ADMIN:
        messages.error(request, 'Требуется роль администратора')
        return redirect('ticket_list')

    users = User.objects.all()
    tickets = Ticket.objects.all()
    return render(request, 'tickets/admin_console.html', {'users': users, 'tickets': tickets})


@login_required
def diagnostics(request):
    profile = ensure_profile(request.user)
    if profile.role != Profile.ROLE_ADMIN:
        messages.error(request, 'Доступ к экрану диагностики разрешен только администраторам.')
        return redirect('ticket_list')

    data = {
        'DEBUG': settings.DEBUG,
        'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
        'MEDIA_ROOT': settings.MEDIA_ROOT,
    }
    return render(request, 'tickets/diagnostics.html', {'data': data})


@login_required
def go_next(request):
    return redirect(request.GET.get('next', '/tickets/'))

@login_required
def handle_role_request(request, request_id):
    profile = ensure_profile(request.user)
    if profile.role != Profile.ROLE_ADMIN:
        messages.error(request, 'Доступ запрещен.')
        return redirect('ticket_list')

    role_request = get_object_or_404(RoleRequest, pk=request_id)
    action = request.POST.get('action')

    if action == 'approve':
        role_request.status = RoleRequest.STATUS_APPROVED
        role_request.save()
        
        # Автоматически меняем роль в профиле пользователя
        user_profile = ensure_profile(role_request.user)
        user_profile.role = role_request.requested_role
        user_profile.save()
        
        messages.success(request, f'Заявка пользователя {role_request.user.username} одобрена. Роль изменена.')
        
    elif action == 'reject':
        role_request.status = RoleRequest.STATUS_REJECTED
        role_request.save()
        messages.warning(request, f'Заявка пользователя {role_request.user.username} отклонена.')

    return redirect('profile_edit')
