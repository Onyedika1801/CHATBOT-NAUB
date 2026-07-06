from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile
from .signals import MAX_ADMIN_ACCOUNTS

admin.site.register(UserProfile)


def _check_unique_email(form, email, instance_pk=None):
    if not email:
        return email
    qs = User.objects.filter(email__iexact=email)
    if instance_pk:
        qs = qs.exclude(pk=instance_pk)
    if qs.exists():
        raise forms.ValidationError(f"An account with the email '{email}' already exists.")
    return email


class CappedUserChangeForm(UserChangeForm):
    """Adds proper form-level checks for the admin-account cap and email
    uniqueness, so hitting either limit shows a normal inline field error
    (and does NOT save, and does NOT show a misleading 'changed successfully'
    message) -- unlike catching the signal's exception after the fact, which
    is too late to stop Django admin's own success-message flow."""

    def clean_is_staff(self):
        is_staff = self.cleaned_data.get('is_staff')
        if is_staff:
            existing = User.objects.filter(is_staff=True).exclude(pk=self.instance.pk)
            if existing.count() >= MAX_ADMIN_ACCOUNTS:
                raise forms.ValidationError(
                    f"Admin accounts are capped at {MAX_ADMIN_ACCOUNTS}. "
                    f"Demote or delete an existing admin account first."
                )
        return is_staff

    def clean_email(self):
        return _check_unique_email(self, self.cleaned_data.get('email'), self.instance.pk)


class CappedUserCreationForm(UserCreationForm):
    """Same email-uniqueness check for the 'Add user' screen."""

    def clean_email(self):
        return _check_unique_email(self, self.cleaned_data.get('email'))


class CappedUserAdmin(BaseUserAdmin):
    form = CappedUserChangeForm
    add_form = CappedUserCreationForm


admin.site.unregister(User)
admin.site.register(User, CappedUserAdmin)
