from django.core.management.base import BaseCommand, CommandError

from apps.schools.models import School
from apps.users.models import User


class Command(BaseCommand):
    help = "Create or update an admin user for the score system"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Login username")
        parser.add_argument("--password", required=True, help="Login password")
        parser.add_argument("--real-name", required=True, help="Display name")
        parser.add_argument("--school-code", default="DEFAULT", help="School code")
        parser.add_argument("--school-name", default="默认学校", help="School name")
        parser.add_argument("--super", action="store_true", dest="is_super", help="Create super admin")

    def handle(self, *args, **options):
        username = options["username"].strip()
        password = options["password"]
        real_name = options["real_name"].strip()
        school_code = options["school_code"].strip()
        school_name = options["school_name"].strip()
        is_super = options["is_super"]

        if not username or not password or not real_name:
            raise CommandError("username/password/real-name are required")

        school, _ = School.objects.get_or_create(
            code=school_code,
            defaults={"name": school_name, "category": "primary", "is_active": True},
        )
        if school.name != school_name:
            school.name = school_name
            school.save(update_fields=["name"])

        role = User.Role.SUPER_ADMIN if is_super else User.Role.ADMIN
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "real_name": real_name,
                "role": role,
                "current_role": role,
                "roles": [role],
                "school": school,
                "is_staff": True,
                "is_superuser": is_super,
            },
        )

        user.real_name = real_name
        user.role = role
        user.current_role = role
        user.roles = [role]
        user.school = school
        user.is_staff = True
        user.is_superuser = is_super
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} admin user: {username} / school={school.code}"))
