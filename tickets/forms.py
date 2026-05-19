import os

from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.models import User
from .models import Attachment, Comment, Profile, Ticket


class SignupForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)

    def save(self):
        return User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data.get('email', ''),
            password=self.cleaned_data['password'],
        )


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'status', 'is_private']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['file']
    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        
        if uploaded_file:
            # 1. Проверяем расширение файла по белому списку
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            allowed_extensions = ['.png', '.jpg', '.jpeg', '.pdf', '.docx', '.doc', '.xlsx', '.txt']
            
            if ext not in allowed_extensions:
                raise ValidationError(
                    f"Недопустимый тип файла. Разрешены только: {', '.join(allowed_extensions)}"
                )
            
            # 2. Ограничиваем максимальный размер файла (например, 5 МБ = 5 * 1024 * 1024 байт)
            max_size = 5 * 1024 * 1024
            if uploaded_file.size > max_size:
                raise ValidationError("Размер файла не должен превышать 5 МБ.")
                
        return uploaded_file
    
    
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone', 'role']
