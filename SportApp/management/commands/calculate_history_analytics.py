from django.core.management.base import BaseCommand
from SportApp.models import Match
from SportApp.analytics import MatchAnalyzer


class Command(BaseCommand):
    help = 'Oblicza wskaźniki historyczne dla zakończonych meczów (Backfill)'

    def handle(self, *args, **options):
        analyzer = MatchAnalyzer()

        self.stdout.write("Pobieranie zakończonych meczów do analizy...")

        matches = Match.objects.filter(status='Finished').order_by('date')

        total = matches.count()
        self.stdout.write(f"Znaleziono {total} zakończonych meczów.")

        updated_count = 0
        skipped_no_stats = 0
        skipped_no_history = 0

        for i, match in enumerate(matches):

            has_stats = (match.home_passes_total or 0) + (match.away_passes_total or 0) > 0

            if not has_stats:
                skipped_no_stats += 1
                if options['verbosity'] > 1:
                    self.stdout.write(self.style.WARNING(f"Pominięto (brak statystyk): {match}"))
                continue

            result = analyzer.calculate_match_analytics(match)

            if result:
                updated_count += 1
            else:
                skipped_no_history += 1
                if options['verbosity'] > 1:
                    self.stdout.write(self.style.WARNING(f"Pominięto (brak historii/too early): {match}"))

            if (i + 1) % 50 == 0:
                self.stdout.write(f"Przetworzono {i + 1}/{total}...")

        self.stdout.write(self.style.SUCCESS("------------------------------------------------"))
        self.stdout.write(self.style.SUCCESS(f"ZAKOŃCZONO BACKFILL."))
        self.stdout.write(f"Zaktualizowano: {updated_count}")
        self.stdout.write(f"Pominięto (brak statystyk w tym meczu): {skipped_no_stats}")
        self.stdout.write(f"Pominięto (brak meczów historycznych - pierwsze kolejki): {skipped_no_history}")