from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from SportApp.models import Match
from SportApp.analytics import MatchAnalyzer


class Command(BaseCommand):
    help = 'Oblicza wskaźniki (Hype, Aggression) dla nadchodzących meczów (okno 7 dni)'

    def handle(self, *args, **options):
        analyzer = MatchAnalyzer()

        now = timezone.now()
        future_limit = now + timedelta(days=7)

        matches = Match.objects.filter(
            status='Scheduled',
            date__range=(now, future_limit)
        ).order_by('date')

        self.stdout.write(f"Znaleziono {matches.count()} meczów w nadchodzącym tygodniu.")

        count = 0
        for match in matches:


            result = analyzer.calculate_match_analytics(match)
            if result:
                count += 1
                if options['verbosity'] > 1:
                    self.stdout.write(f"Zaktualizowano analizę: {match}")
            else:
                if options['verbosity'] > 1:
                    self.stdout.write(self.style.WARNING(f"Za mało danych dla: {match}"))

        self.stdout.write(
            self.style.SUCCESS(f"Zakończono. Zaktualizowano analizy dla {count} meczów z najbliższych 7 dni."))