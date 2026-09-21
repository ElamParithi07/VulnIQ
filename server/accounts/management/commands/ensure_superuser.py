import os

from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = (
        "Idempotently ensure a superuser exists, reading DJANGO_SUPERUSER_EMAIL and "
        "DJANGO_SUPERUSER_PASSWORD from the environment. Safe to run on every deploy: "
        "a no-op once the user already exists. Does nothing if either env var is unset."
    )

    def handle(self, *args, **options):
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not email or not password:
            self.stdout.write("DJANGO_SUPERUSER_EMAIL/PASSWORD not set; skipping.")
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(f"Superuser {email} already exists; skipping.")
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser {email}."))
