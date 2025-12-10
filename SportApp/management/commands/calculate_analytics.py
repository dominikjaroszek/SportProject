from django.core.management.base import BaseCommand
from django.utils import timezone  # Ważny import do obsługi czasu
from datetime import timedelta  # Do dodawania dni
from SportApp.models import Match
from SportApp.analytics import MatchAnalyzer


class Command(BaseCommand):
    help = 'Oblicza wskaźniki (Hype, Aggression) dla nadchodzących meczów (okno 7 dni)'

    def handle(self, *args, **options):
        analyzer = MatchAnalyzer()

        # Ustal obecny czas
        now = timezone.now()

        # Ustal "horyzont" czasowy - np. 7 dni do przodu
        # To zależy od Twojego biznesu: czy użytkownicy patrzą na mecze za 2 tygodnie?
        # Zazwyczaj 7 dni jest optymalne dla piłki nożnej.
        future_limit = now + timedelta(days=7)

        # Wybieramy mecze zaplanowane TYLKO na najbliższy tydzień
        matches = Match.objects.filter(
            status='Scheduled',
            date__range=(now, future_limit)  # Zakres od teraz do +7 dni
        ).order_by('date')

        self.stdout.write(f"Znaleziono {matches.count()} meczów w nadchodzącym tygodniu.")

        count = 0
        for match in matches:
            # Tu jest ważny moment:
            # Ponieważ wskaźniki się zmieniają, zazwyczaj chcemy je NADPISAĆ,
            # nawet jeśli już istnieją (bo np. wczorajszy mecz innej drużyny zmienił hype).

            result = analyzer.calculate_match_analytics(match)
            if result:
                count += 1
                # Możesz dodać verbosity, żeby nie spamować konsoli przy cronie
                if options['verbosity'] > 1:
                    self.stdout.write(f"Zaktualizowano analizę: {match}")
            else:
                if options['verbosity'] > 1:
                    self.stdout.write(self.style.WARNING(f"Za mało danych dla: {match}"))

        self.stdout.write(
            self.style.SUCCESS(f"Zakończono. Zaktualizowano analizy dla {count} meczów z najbliższych 7 dni."))