from django.core.management.base import BaseCommand
from SportApp.models import Match, AnalyticsBenchmark
import statistics


class Command(BaseCommand):
    help = 'Wyznacza limity (Cap) statystyk, ignorując puste mecze i wymuszając minimum.'

    def handle(self, *args, **options):
        matches = Match.objects.filter(status='Finished').order_by('-date')[:1000]

        if not matches:
            self.stdout.write(self.style.WARNING("Brak meczów."))
            return

        fields_to_analyze = [
            'blocked_shots', 'offsides', 'passes_total', 'passes_accurate',
            'shots_inside_box', 'corners', 'shots_on_goal',
            'fouls', 'yellow_cards', 'red_cards'
        ]

        MIN_LIMITS = {
            'red_cards': 1.0,
            'yellow_cards': 3.0,
            'offsides': 2.0,
            'shots_on_goal': 3.0,
            'passes_total': 300.0,
        }

        raw_data = {field: [] for field in fields_to_analyze}

        skipped_count = 0
        valid_count = 0

        self.stdout.write(f"Analizuję {len(matches)} meczów...")

        for m in matches:
            total_passes = (m.home_passes_total or 0) + (m.away_passes_total or 0)
            if total_passes == 0:
                skipped_count += 1
                continue

            valid_count += 1

            for field in fields_to_analyze:
                val_h = getattr(m, f'home_{field}', 0) or 0
                val_a = getattr(m, f'away_{field}', 0) or 0

                raw_data[field].append(val_h)
                raw_data[field].append(val_a)

        if valid_count == 0:
            self.stdout.write(self.style.ERROR("Wszystkie mecze miały puste statystyki (0 podań)!"))
            return

        self.stdout.write(f"Pominięto {skipped_count} pustych meczów. Przeanalizowano {valid_count} poprawnych.")

        for field, values in raw_data.items():
            if not values: continue

            values.sort()
            count = len(values)

            idx = int(count * 0.95)
            idx = min(idx, count - 1)

            calculated_limit = values[idx]

            min_limit = MIN_LIMITS.get(field, 0.0)
            final_limit = max(calculated_limit, min_limit)

            avg_val = statistics.mean(values)
            stat_key = f"limit_{field}"

            AnalyticsBenchmark.objects.update_or_create(
                stat_name=stat_key,
                defaults={
                    'benchmark_value': final_limit,
                    'avg_value': avg_val,
                    'sample_size': count
                }
            )

            msg = f"{field}: Wyliczono={calculated_limit} -> Zapisano={final_limit} (Średnia={avg_val:.1f})"
            if calculated_limit < min_limit:
                self.stdout.write(self.style.WARNING(msg + " [WYMUSZONO MINIMUM]"))
            else:
                self.stdout.write(self.style.SUCCESS(msg))