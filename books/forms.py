"""
User-facing forms for profile management and other user interactions
"""
from django import forms
from django.contrib.auth import get_user_model
from .models import UserProfile


User = get_user_model()


class ProfileEditForm(forms.ModelForm):
    """Form for editing user profile including avatar upload"""
    
    class Meta:
        model = UserProfile
        fields = ['display_name', 'bio', 'location', 'website', 'avatar', 'avatar_url']
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Display name'
            }),
            'bio': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Tell us about yourself...',
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Location'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://yourwebsite.com'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'avatar_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/avatar.jpg'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].required = False
        self.fields['avatar_url'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        avatar = cleaned_data.get('avatar')
        avatar_url = cleaned_data.get('avatar_url')
        
        # If both avatar and avatar_url are provided, prefer the uploaded file
        if avatar and avatar_url:
            cleaned_data['avatar_url'] = ''
        
        return cleaned_data