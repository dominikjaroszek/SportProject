from django.core.management.base import BaseCommand
from django.db.models import Q
from SportApp.models import Match
from SportApp.analytics import MatchAnalyzer


class Command(BaseCommand):
    help = 'Oblicza wskaźniki historyczne dla zakończonych meczów (Backfill)'

    def handle(self, *args, **options):
        analyzer = MatchAnalyzer()

        self.stdout.write("Pobieranie zakończonych meczów do analizy...")

        # 1. Pobieramy wszystkie zakończone mecze, posortowane chronologicznie
        # Sortowanie od najstarszych jest ważne, żeby analityka miała "ciągłość" logiczną
        matches = Match.objects.filter(status='Finished').order_by('date')

        total = matches.count()
        self.stdout.write(f"Znaleziono {total} zakończonych meczów.")

        updated_count = 0
        skipped_no_stats = 0
        skipped_no_history = 0

        # Pasek postępu w prostym wydaniu (co 50 meczów)
        for i, match in enumerate(matches):

            # 2. Sprawdzenie, czy mecz ma pobrane statystyki
            # (Twoje wymaganie: "obliczamy to dla meczów co tylko mają statystyki pobrane")
            has_stats = (match.home_passes_total or 0) + (match.away_passes_total or 0) > 0

            if not has_stats:
                skipped_no_stats += 1
                if options['verbosity'] > 1:
                    self.stdout.write(self.style.WARNING(f"Pominięto (brak statystyk): {match}"))
                continue

            # 3. Uruchomienie analizera
            # Analyzer sam pobiera 5 poprzednich meczów.
            # Jeśli jest to np. 1. mecz sezonu i nie ma historii, analyzer może zwrócić None
            # (zależnie od implementacji w calculate_match_analytics 'if not home_last_5')
            result = analyzer.calculate_match_analytics(match)

            if result:
                updated_count += 1
            else:
                skipped_no_history += 1
                if options['verbosity'] > 1:
                    self.stdout.write(self.style.WARNING(f"Pominięto (brak historii/too early): {match}"))

            # Log co 50 meczów, żeby widzieć postęp
            if (i + 1) % 50 == 0:
                self.stdout.write(f"Przetworzono {i + 1}/{total}...")

        self.stdout.write(self.style.SUCCESS("------------------------------------------------"))
        self.stdout.write(self.style.SUCCESS(f"ZAKOŃCZONO BACKFILL."))
        self.stdout.write(f"Zaktualizowano: {updated_count}")
        self.stdout.write(f"Pominięto (brak statystyk w tym meczu): {skipped_no_stats}")
        self.stdout.write(f"Pominięto (brak meczów historycznych - pierwsze kolejki): {skipped_no_history}")