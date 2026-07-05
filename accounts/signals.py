from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

# Hard cap on the number of staff/admin accounts (accounts that can log into
# /dashboard/ and /admin/). This is enforced at the database-signal level so
# it applies no matter how the account is created -- Django admin, the
# createsuperuser management command, the Python shell, everywhere.
MAX_ADMIN_ACCOUNTS = 3


@receiver(pre_save, sender=User)
def enforce_admin_account_limit(sender, instance, **kwargs):
    if not instance.is_staff:
        return

    existing_staff_qs = User.objects.filter(is_staff=True)
    if instance.pk:
        existing_staff_qs = existing_staff_qs.exclude(pk=instance.pk)

    if existing_staff_qs.count() >= MAX_ADMIN_ACCOUNTS:
        raise ValidationError(
            f"Cannot create/promote this account -- NAUB Chatbot admin accounts "
            f"are capped at {MAX_ADMIN_ACCOUNTS}. Demote or delete an existing "
            f"admin account first."
        )
