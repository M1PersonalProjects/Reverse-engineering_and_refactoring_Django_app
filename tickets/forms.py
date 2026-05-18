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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone', 'role']
