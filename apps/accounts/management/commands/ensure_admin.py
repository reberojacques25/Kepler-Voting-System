"""Create the first admin account from environment variables.

Hosting free tiers often have no shell, so `createsuperuser` can't be run by
hand. The build script runs this instead; it does nothing if the variables are
unset or the account already exists, so it is safe to run on every deploy.

    DJANGO_ADMIN_EMAIL=admin@kepler.ac.rw
    DJANGO_ADMIN_PASSWORD=...
    DJANGO_ADMIN_STUDENT_ID=ADMIN-001   (optional)
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the initial staff/superuser account from DJANGO_ADMIN_* env vars."

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "")
        if not email or not password:
            self.stdout.write("ensure_admin: DJANGO_ADMIN_EMAIL/PASSWORD not set, skipping.")
            return

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(f"ensure_admin: {email} already exists, leaving it unchanged.")
            return

        User.objects.create_superuser(
            username=email,
            email=email,
            password=password,
            student_id=os.environ.get("DJANGO_ADMIN_STUDENT_ID", "ADMIN-001"),
            is_email_verified=True,
        )
        self.stdout.write(self.style.SUCCESS(f"ensure_admin: created admin {email}."))
