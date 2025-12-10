from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Tworzy domyślne grupy (User, Admin)'

    def handle(self, *args, **options):
        admin_group, created = Group.objects.get_or_create(name='Admin')
        user_group, created = Group.objects.get_or_create(name='User')

        self.stdout.write(self.style.SUCCESS("Grupy Admin i User są gotowe."))