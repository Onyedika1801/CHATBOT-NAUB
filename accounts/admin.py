from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User
from .models import UserProfile
from .signals import MAX_ADMIN_ACCOUNTS

admin.site.register(UserProfile)


class CappedUserChangeForm(UserChangeForm):
    """Adds a proper form-level check for the admin-account cap, so hitting
    the limit shows a normal inline field error (and does NOT save, and does
    NOT show a misleading 'changed successfully' message) -- unlike catching
    the signal's exception after the fact, which is too late to stop Django
    admin's own success-message flow."""

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


class CappedUserAdmin(BaseUserAdmin):
    form = CappedUserChangeForm


admin.site.unregister(User)
admin.site.register(User, CappedUserAdmin)
