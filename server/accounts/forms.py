from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Organization, User


class SignUpForm(forms.ModelForm):
    organization_name = forms.CharField(max_length=255)
    organization_slug = forms.SlugField(max_length=100)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_organization_slug(self):
        slug = self.cleaned_data["organization_slug"]
        if Organization.objects.filter(slug=slug).exists():
            raise forms.ValidationError("This organization slug is already in use.")
        return slug

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    def save(self, commit: bool = True):
        organization = Organization.objects.create(
            name=self.cleaned_data["organization_name"],
            slug=self.cleaned_data["organization_slug"],
        )
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            organization=organization,
        )
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")
