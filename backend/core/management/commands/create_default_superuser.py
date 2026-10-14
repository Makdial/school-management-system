"""Create the bootstrap super administrator idempotently.

Credentials are read from the environment so no secret is ever committed:

    DJANGO_SUPERUSER_USERNAME (default: superadmin)
    DJANGO_SUPERUSER_EMAIL    (default: admin@example.com)
    DJANGO_SUPERUSER_PASSWORD (required)

Usage::

    python manage.py create_default_superuser
    python manage.py create_default_superuser --password S3cret
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the default super administrator if it does not already exist."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.getenv("DJANGO_SUPERUSER_USERNAME", "superadmin"))
        parser.add_argument("--email", default=os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com"))
        parser.add_argument("--password", default=os.getenv("DJANGO_SUPERUSER_PASSWORD"))

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        email = self.email
        password = options["password"] or os.getenv("DJANGO_SUPERUSER_PASSWORD")
        email = options["email"]

        if not password:
            raise CommandError(
                "No password provided. Set DJANGO_SUPERUSER_PASSWORD or pass --password."
            )

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "user_type": "SUPERADMIN",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if created:
            user.set_password(self.password or os.getenv("DJANGO_SUPERUSER_PASSWORD"))
            user.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}'."))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists."))
