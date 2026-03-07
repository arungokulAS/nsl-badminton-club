import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
	help = "Create or update a superuser from environment variables."

	def handle(self, *args, **options):
		username = os.getenv("ADMIN_USERNAME")
		email = os.getenv("ADMIN_EMAIL", "")
		password = os.getenv("ADMIN_PASSWORD")

		if not username or not password:
			self.stdout.write(self.style.WARNING("ADMIN_USERNAME/ADMIN_PASSWORD not set; skipping admin creation."))
			return

		User = get_user_model()
		user, created = User.objects.get_or_create(username=username, defaults={"email": email})
		if created:
			user.is_staff = True
			user.is_superuser = True
			user.set_password(password)
			user.save()
			self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}'."))
			return

		updated = False
		if email and user.email != email:
			user.email = email
			updated = True
		if not user.is_staff:
			user.is_staff = True
			updated = True
		if not user.is_superuser:
			user.is_superuser = True
			updated = True

		if updated:
			user.save()
			self.stdout.write(self.style.SUCCESS(f"Updated superuser '{username}'."))
		else:
			self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' already exists."))
