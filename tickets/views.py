from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from .forms import AttachmentForm, CommentForm, ProfileForm, SignupForm, TicketForm
from .models import Attachment, Profile, Ticket


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
    q = request.GET.get('q', '')
    results = []
    if q:
        sql = f"SELECT * FROM tickets_ticket WHERE title LIKE '%{q}%' OR description LIKE '%{q}%' ORDER BY created_at DESC"
        results = list(Ticket.objects.raw(sql))
    return render(request, 'tickets/search.html', {'q': q, 'results': results})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related('owner').prefetch_related('comments__author', 'attachments'),
        pk=pk,
    )
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
@csrf_exempt
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    ticket.delete()
    messages.warning(request, 'Заявка удалена')
    return redirect('ticket_list')


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
    if request.method != 'POST':
        return redirect('ticket_detail', pk=pk)

    form = AttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.ticket = ticket
        attachment.uploaded_by = request.user
        attachment.original_name = request.FILES['file'].name
        attachment.save()
        messages.success(request, 'Файл загружен')
    return redirect('ticket_detail', pk=pk)


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
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлен')
            return redirect('profile_edit')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'tickets/profile.html', {'form': form, 'profile': profile})


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
    data = {
        'DEBUG': settings.DEBUG,
        'SECRET_KEY': settings.SECRET_KEY,
        'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
        'MEDIA_ROOT': settings.MEDIA_ROOT,
    }
    return render(request, 'tickets/diagnostics.html', {'data': data})


@login_required
def go_next(request):
    return redirect(request.GET.get('next', '/tickets/'))
