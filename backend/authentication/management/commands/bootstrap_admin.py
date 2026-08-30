from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the bootstrap admin user if it does not exist."

    def handle(self, *args, **options) -> None:
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username="admin",
            defaults={
                "role": user_model.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            user.set_password(settings.ADMIN_BOOTSTRAP_PASSWORD)
            user.save()
            self.stdout.write(self.style.SUCCESS("Created bootstrap admin user."))
            return
        if user.role != user_model.Role.ADMIN:
            user.role = user_model.Role.ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["role", "is_staff", "is_superuser"])
        self.stdout.write("Bootstrap admin user already exists.")
