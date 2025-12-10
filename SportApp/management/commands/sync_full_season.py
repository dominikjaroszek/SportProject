from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from SportApp.models import League, Season, Team, Match, Standing, TopScorer
from SportApp.services import FootballAPIService
import time


class Command(BaseCommand):
    def handle(self, *args, **options):
        service = FootballAPIService()


        LEAGUES_TO_SYNC = [39]
        TARGET_SEASON = 2025

        for league_id in LEAGUES_TO_SYNC:
            self.stdout.write(self.style.WARNING(f"--- Rozpoczynam ligę {league_id} (Sezon {TARGET_SEASON}) ---"))

            league_data_list = service.get_league_info(league_id)
            if not league_data_list:
                self.stdout.write(self.style.ERROR(f"Brak danych dla ligi {league_id}"))
                continue

            l_info = league_data_list[0]['league']
            c_info = league_data_list[0]['country']

            league_obj, _ = League.objects.update_or_create(
                api_id=l_info['id'],
                defaults={
                    'name': l_info['name'],
                    'country': c_info['name'],
                    'logo': l_info['logo']
                }
            )
            self.stdout.write(f"Zaktualizowano ligę: {league_obj.name}")

            # ==========================================
            # KROK 2: UTWORZENIE SEZONU
            # ==========================================
            season_obj, created = Season.objects.update_or_create(
                league=league_obj,
                year=TARGET_SEASON,
                defaults={'is_current': True}
            )

            # ==========================================
            # KROK 3: POBIERANIE DRUŻYN
            # ==========================================
            self.stdout.write("Pobieranie drużyn...")
            teams_data = service.get_teams(league_id, TARGET_SEASON)

            for item in teams_data:
                t = item['team']
                v = item['venue']

                Team.objects.update_or_create(
                    api_id=t['id'],
                    defaults={
                        'league': league_obj,  # <--- TUTAJ PRZYPISUJEMY LIGĘ NA SZTYWNO
                        'name': t['name'],
                        'logo': t['logo'],
                        'founded': t['founded'],
                        'venue_name': v['name'],
                        'venue_city': v['city'],
                        'venue_capacity': v['capacity']
                    }
                )

            # Pauza dla API (bezpieczeństwo Rate Limit)
            time.sleep(2)

            # ==========================================
            # KROK 4: POBIERANIE MECZÓW (FIXTURES)
            # ==========================================
            self.stdout.write("Pobieranie meczów...")
            fixtures = service.get_fixtures(league_id, TARGET_SEASON)

            match_counter = 0
            for item in fixtures:
                fixture = item['fixture']
                goals = item['goals']
                teams = item['teams']
                league_resp = item['league']

                # Parsowanie daty i strefy czasowej
                match_date = parse_datetime(fixture['date'])
                if timezone.is_naive(match_date):
                    match_date = timezone.make_aware(match_date)

                # Próba pobrania drużyn z bazy
                try:
                    home_team = Team.objects.get(api_id=teams['home']['id'])
                    away_team = Team.objects.get(api_id=teams['away']['id'])
                except Team.DoesNotExist:
                    # Jeśli drużyny nie ma (rzadki przypadek), pomijamy mecz
                    continue

                current_status_short = fixture['status']['short']
                readable_status = self.get_match_type_status(current_status_short)

                Match.objects.update_or_create(
                    api_id=fixture['id'],
                    defaults={
                        'season': season_obj,
                        'home_team': home_team,
                        'away_team': away_team,
                        'date': match_date,
                        'home_score': goals['home'],
                        'away_score': goals['away'],
                        'referee': fixture['referee'],
                        'venue_name': fixture['venue']['name'],
                        'round': league_resp['round'],
                        'status': readable_status,
                    }
                )
                match_counter += 1

            self.stdout.write(f"Przetworzono {match_counter} meczów.")
            time.sleep(2)

            # ==========================================
            # KROK 5: TABELA (STANDINGS)
            # ==========================================
            self.stdout.write("Pobieranie tabeli...")
            standings_resp = service.get_standings(league_id, TARGET_SEASON)

            if standings_resp:
                # Struktura API: response -> league -> standings -> [ [TeamA, TeamB...] ]
                # Zazwyczaj indeks [0] to główna tabela
                try:
                    standings_list = standings_resp[0]['league']['standings'][0]

                    for row in standings_list:
                        team_api_id = row['team']['id']
                        try:
                            team_obj = Team.objects.get(api_id=team_api_id)

                            Standing.objects.update_or_create(
                                season=season_obj,
                                team=team_obj,
                                defaults={
                                    'position': row['rank'],
                                    'points': row['points'],
                                    'form': row['form'],

                                    # Nowe nazwy pól:
                                    'status': row['status'],
                                    'last_update': parse_datetime(row['update']),  # Zmiana na last_update

                                    # Ogólne
                                    'played': row['all']['played'],
                                    'win': row['all']['win'],
                                    'draw': row['all']['draw'],
                                    'lose': row['all']['lose'],
                                    'goals_for': row['all']['goals']['for'],  # Zmiana na goals_for
                                    'goals_against': row['all']['goals']['against'],  # Zmiana na goals_against
                                    'goals_diff': row['goalsDiff'],

                                    # DOM
                                    'home_played': row['home']['played'],
                                    'home_win': row['home']['win'],
                                    'home_draw': row['home']['draw'],
                                    'home_lose': row['home']['lose'],
                                    'home_goals_for': row['home']['goals']['for'],  # Zmiana
                                    'home_goals_against': row['home']['goals']['against'],  # Zmiana

                                    # WYJAZD
                                    'away_played': row['away']['played'],
                                    'away_win': row['away']['win'],
                                    'away_draw': row['away']['draw'],
                                    'away_lose': row['away']['lose'],
                                    'away_goals_for': row['away']['goals']['for'],  # Zmiana
                                    'away_goals_against': row['away']['goals']['against'],  # Zmiana
                                }
                            )
                        except Team.DoesNotExist:
                            continue
                except (IndexError, KeyError):
                    self.stdout.write(self.style.ERROR("Problem ze strukturą tabeli w API"))

            time.sleep(2)

            # ==========================================
            # KROK 6: KRÓLOWIE STRZELCÓW
            # ==========================================
            self.stdout.write("Pobieranie strzelców...")
            scorers = service.get_top_scorers(league_id, TARGET_SEASON)

            if scorers:
                # Wyczyść starych strzelców dla tego sezonu, żeby nie dublować
                TopScorer.objects.filter(season=season_obj).delete()

                for sc in scorers:
                    player = sc['player']
                    stats = sc['statistics'][0]
                    team_id = stats['team']['id']

                    try:
                        team_obj = Team.objects.get(api_id=team_id)
                        TopScorer.objects.create(
                            season=season_obj,
                            team=team_obj,
                            player_name=player['name'],
                            # Opcjonalnie: player_api_id=player['id'],
                            goals=stats['goals']['total'] or 0,
                            assists=stats['goals']['assists'] or 0
                        )
                    except Team.DoesNotExist:
                        continue

            self.stdout.write(self.style.SUCCESS(f"Zakończono ligę {league_id}"))

    @staticmethod
    def get_match_type_status(short):
        """
        Mapuje status API na czytelny format.
        Zawiera wszystkie przypadki z Twojego kodu Flask.
        """
        STATUS_MAP = {
            # SCHEDULED
            'TBD': 'Scheduled',
            'NS': 'Scheduled',

            # IN PLAY
            '1H': 'In Play',
            'HT': 'In Play',
            '2H': 'In Play',
            'ET': 'In Play',
            'BT': 'In Play',
            'P': 'In Play',
            'LIVE': 'In Play',
            'SUSP': 'In Play',  # Dodane z Twojej listy
            'INT': 'In Play',  # Dodane z Twojej listy

            # FINISHED
            'FT': 'Finished',
            'AET': 'Finished',
            'PEN': 'Finished',  # W API-Football PEN to koniec meczu po karnych

            # OTHER
            'PST': 'Postponed',
            'CANC': 'Cancelled',
            'ABD': 'Abandoned',
            'AWD': 'Not Played',
            'WO': 'Not Played'
        }
        # get(klucz, wartość_domyślna) - jak nie znajdzie, zwróci sam kod (np. 'XYZ')
        return STATUS_MAP.get(short, short)