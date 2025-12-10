from django.core.management.base import BaseCommand
from SportApp.models import Match
from SportApp.services import FootballAPIService
import time


class Command(BaseCommand):
    help = 'Pobiera brakujące statystyki dla zakończonych meczów'

    def handle(self, *args, **options):
        service = FootballAPIService()

        # 1. Znajdź mecze, które są zakończone, ale nie mają jeszcze statystyk (np. home_total_shots jest NULL)
        # Dzięki temu nie pobieramy w kółko tego samego.
        matches_to_update = Match.objects.filter(
            status="Finished",
            home_total_shots__isnull=True
        ).order_by('-date')[:60]  # Od najnowszych

        #total_count = matches_to_update.count()
        total_count = len(matches_to_update)
        self.stdout.write(f"Znaleziono {total_count} meczów wymagających pobrania statystyk.")

        for i, match in enumerate(matches_to_update):
            self.stdout.write(f"[{i + 1}/{total_count}] Pobieranie statystyk dla meczu ID {match.api_id}...")

            # Pobieramy dane z API
            stats_data = service.get_fixture_statistics(match.api_id)

            # API zwraca pustą listę [], jeśli nie ma statystyk dla meczu
            if not stats_data:
                self.stdout.write(self.style.WARNING(f"Brak statystyk w API dla meczu {match.api_id}"))
                # Oznaczamy np. blocked_shots jako 0, żeby pętla nie brała tego meczu następnym razem
                # match.home_total_shots = 0
                # match.save()
                time.sleep(1)  # Krótka pauza mimo braku danych
                continue

            # API zwraca listę dwóch obiektów: jeden dla Team A, drugi dla Team B
            # Musimy dopasować, który to Home, a który Away
            for item in stats_data:
                team_id = item['team']['id']
                stats_list = item['statistics']

                # Sprawdzamy, czy to drużyna gospodarzy czy gości
                if team_id == match.home_team.api_id:
                    prefix = 'home_'
                elif team_id == match.away_team.api_id:
                    prefix = 'away_'
                else:
                    continue  # Dziwny przypadek, pomijamy

                # Mapowanie dziwnych nazw z API na Twoje pola w modelu
                for stat in stats_list:
                    stat_type = stat['type']  # np. "Shots on Goal"
                    stat_value = stat['value']  # np. 5 lub None

                    # Jeśli wartość to None, zamień na 0 (chyba że wolisz None)
                    if stat_value is None:
                        stat_value = 0

                    if stat_type == 'Shots on Goal':
                        setattr(match, f'{prefix}shots_on_goal', stat_value)
                    elif stat_type == 'Shots off Goal':
                        setattr(match, f'{prefix}shots_off_goal', stat_value)
                    elif stat_type == 'Total Shots':
                        setattr(match, f'{prefix}total_shots', stat_value)
                    elif stat_type == 'Blocked Shots':
                        setattr(match, f'{prefix}blocked_shots', stat_value)
                    elif stat_type == 'Fouls':
                        setattr(match, f'{prefix}fouls', stat_value)
                    elif stat_type == 'Corner Kicks':
                        setattr(match, f'{prefix}corners', stat_value)
                    elif stat_type == 'Offsides':
                        setattr(match, f'{prefix}offsides', stat_value)
                    elif stat_type == 'Ball Possession':
                        # API zwraca np. "50%", my chcemy zapisać jako string
                        setattr(match, f'{prefix}possession', str(stat_value))
                    elif stat_type == 'Yellow Cards':
                        setattr(match, f'{prefix}yellow_cards', stat_value)
                    elif stat_type == 'Red Cards':
                        setattr(match, f'{prefix}red_cards', stat_value)
                    elif stat_type == 'Total passes':
                        setattr(match, f'{prefix}passes_total', stat_value)
                    elif stat_type == 'Passes accurate':
                        setattr(match, f'{prefix}passes_accurate', stat_value)
                    elif stat_type == 'Goalkeeper saves':
                        setattr(match, f'{prefix}goalkeeper_saves', stat_value)
                    elif stat_type == 'Shots inside box':
                        setattr(match, f'{prefix}shots_inside_box', stat_value)
                    elif stat_type == 'Shots outside box':
                        setattr(match, f'{prefix}shots_outside_box', stat_value)

            match.save()

            time.sleep(7)

        self.stdout.write(self.style.SUCCESS("Zakończono aktualizację statystyk."))