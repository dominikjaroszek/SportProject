from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Nadaje uprawnienia is_superuser oraz is_staff użytkownikowi o podanym emailu.'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email użytkownika do awansowania')

    def handle(self, *args, **options):
        email = options['email']
        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)

            if user.is_superuser:
                self.stdout.write(self.style.WARNING(f'Użytkownik "{email}" jest już superuserem.'))
            else:
                user.is_superuser = True
                user.is_staff = True
                user.save()

                self.stdout.write(self.style.SUCCESS(f'Pomyślnie nadano uprawnienia superusera dla "{email}"'))

        except User.DoesNotExist:
            raise CommandError(f'Użytkownik o adresie email "{email}" nie istnieje.')
        except Exception as e:
            raise CommandError(f'Wystąpił nieoczekiwany błąd: {str(e)}')