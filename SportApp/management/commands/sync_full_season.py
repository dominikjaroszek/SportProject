from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from SportApp.models import League, Season, Team, Match, Standing, TopScorer
from SportApp.services import FootballAPIService
import time


class Command(BaseCommand):
    help = 'Aktualizuje dane sportowe z API z możliwością wyboru zakresu danych.'

    def add_arguments(self, parser):
        # Flagi pozwalające sterować tym, co pobieramy
        parser.add_argument(
            '--setup',
            action='store_true',
            help='Pobiera dane statyczne: Ligę, Sezon i Drużyny (uruchamiaj rzadko)',
        )
        parser.add_argument(
            '--matches',
            action='store_true',
            help='Pobiera i aktualizuje mecze (fixtures)',
        )
        parser.add_argument(
            '--standings',
            action='store_true',
            help='Pobiera tabele i królów strzelców',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Wykonuje wszystkie powyższe akcje',
        )

    def handle(self, *args, **options):
        service = FootballAPIService()

        # Konfiguracja
        LEAGUES_TO_SYNC = [311]  # Premier League
        TARGET_SEASON = 2025

        # Sprawdzenie co użytkownik chce zrobić
        do_setup = options['setup'] or options['all']
        do_matches = options['matches'] or options['all']
        do_standings = options['standings'] or options['all']

        # Jeśli nie podano żadnej flagi, wyświetl info i zakończ
        if not any([do_setup, do_matches, do_standings]):
            self.stdout.write(
                self.style.WARNING("Nie wybrano żadnej akcji. Użyj --setup, --matches, --standings lub --all"))
            return

        for league_id in LEAGUES_TO_SYNC:
            self.stdout.write(self.style.WARNING(f"--- Przetwarzanie ligi {league_id} (Sezon {TARGET_SEASON}) ---"))

            # Pobieramy lub tworzymy obiekt ligi/sezonu, który jest potrzebny w każdym kroku
            # Robimy to "leniwie" - pobieramy z bazy, a z API tylko jeśli wymuszono --setup
            league_obj = None
            season_obj = None

            # ==========================================
            # KROK 1 & 2 & 3: SETUP (Liga, Sezon, Drużyny)
            # Koszt API: 2 zapytania (1x League info, 1x Teams)
            # ==========================================
            if do_setup:
                self.stdout.write("Tryb SETUP: Pobieranie danych o lidze i drużynach...")

                # 1. Liga Info
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

                # 2. Sezon
                season_obj, _ = Season.objects.update_or_create(
                    league=league_obj,
                    year=TARGET_SEASON,
                    defaults={'is_current': True}
                )

                # 3. Drużyny
                teams_data = service.get_teams(league_id, TARGET_SEASON)
                for item in teams_data:
                    t = item['team']
                    v = item['venue']
                    Team.objects.update_or_create(
                        api_id=t['id'],
                        defaults={
                            'league': league_obj,
                            'name': t['name'],
                            'logo': t['logo'],
                            'founded': t['founded'],
                            'venue_name': v['name'],
                            'venue_city': v['city'],
                            'venue_capacity': v['capacity']
                        }
                    )
                self.stdout.write(self.style.SUCCESS("Zakończono SETUP."))
                time.sleep(1)  # Pauza dla bezpieczeństwa

            else:
                # Jeśli nie robimy setupu, musimy pobrać obiekty z bazy, żeby przypisać je do meczów/tabeli
                try:
                    league_obj = League.objects.get(api_id=league_id)
                    season_obj = Season.objects.get(league=league_obj, year=TARGET_SEASON)
                except (League.DoesNotExist, Season.DoesNotExist):
                    self.stdout.write(self.style.ERROR("Brak ligi/sezonu w bazie. Uruchom najpierw z flagą --setup"))
                    continue

            # ==========================================
            # KROK 4: MECZE
            # Koszt API: 1 zapytanie
            # ==========================================
            if do_matches:
                self.stdout.write("Tryb MATCHES: Aktualizacja wyników...")
                fixtures = service.get_fixtures(league_id, TARGET_SEASON)

                # --- DEBUG 1: Sprawdzamy czy API w ogóle coś zwróciło ---
                if not fixtures:
                    self.stdout.write(
                        self.style.ERROR("API zwróciło pustą listę meczów! Sprawdź klucz API lub rok sezonu."))

                updated_count = 0
                for item in fixtures:
                    fixture = item['fixture']
                    goals = item['goals']
                    teams = item['teams']
                    league_resp = item['league']

                    match_date = parse_datetime(fixture['date'])
                    if timezone.is_naive(match_date):
                        match_date = timezone.make_aware(match_date)

                    try:
                        home_team = Team.objects.get(api_id=teams['home']['id'])
                        away_team = Team.objects.get(api_id=teams['away']['id'])
                    except Team.DoesNotExist:
                        # --- DEBUG 2: Sprawdzamy czy blokuje nas brak drużyny w bazie ---
                        self.stdout.write(self.style.WARNING(
                            f"Pomijam mecz {fixture['id']}: Brak drużyny w bazie! (Home ID: {teams['home']['id']}, Away ID: {teams['away']['id']})"
                        ))
                        continue

                    readable_status = self.get_match_type_status(fixture['status']['short'])

                    # Update or create
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
                    updated_count += 1

                self.stdout.write(self.style.SUCCESS(f"Zaktualizowano {updated_count} meczów."))
                time.sleep(1)

            # ==========================================
            # KROK 5 & 6: TABELA I STRZELCY
            # Koszt API: 2 zapytania (1x Standings, 1x Scorers)
            # ==========================================
            if do_standings:
                self.stdout.write("Tryb STANDINGS: Aktualizacja tabeli i strzelców...")

                # 1. Tabela
                standings_resp = service.get_standings(league_id, TARGET_SEASON)
                if standings_resp:
                    try:
                        standings_list = standings_resp[0]['league']['standings'][0]
                        for row in standings_list:
                            try:
                                team_obj = Team.objects.get(api_id=row['team']['id'])
                                Standing.objects.update_or_create(
                                    season=season_obj,
                                    team=team_obj,
                                    defaults={
                                        'position': row['rank'],
                                        'points': row['points'],
                                        'form': row['form'],
                                        'status': row['status'],
                                        'last_update': parse_datetime(row['update']),
                                        'played': row['all']['played'],
                                        'win': row['all']['win'],
                                        'draw': row['all']['draw'],
                                        'lose': row['all']['lose'],
                                        'goals_for': row['all']['goals']['for'],
                                        'goals_against': row['all']['goals']['against'],
                                        'goals_diff': row['goalsDiff'],
                                        'home_played': row['home']['played'],
                                        'home_win': row['home']['win'],
                                        'home_draw': row['home']['draw'],
                                        'home_lose': row['home']['lose'],
                                        'home_goals_for': row['home']['goals']['for'],
                                        'home_goals_against': row['home']['goals']['against'],
                                        'away_played': row['away']['played'],
                                        'away_win': row['away']['win'],
                                        'away_draw': row['away']['draw'],
                                        'away_lose': row['away']['lose'],
                                        'away_goals_for': row['away']['goals']['for'],
                                        'away_goals_against': row['away']['goals']['against'],
                                    }
                                )
                            except Team.DoesNotExist:
                                pass
                    except (IndexError, KeyError):
                        self.stdout.write(self.style.ERROR("Błąd struktury tabeli"))

                # 2. Strzelcy
                scorers = service.get_top_scorers(league_id, TARGET_SEASON)
                if scorers:
                    TopScorer.objects.filter(season=season_obj).delete()
                    for sc in scorers:
                        stats = sc['statistics'][0]
                        try:
                            team_obj = Team.objects.get(api_id=stats['team']['id'])
                            TopScorer.objects.create(
                                season=season_obj,
                                team=team_obj,
                                player_name=sc['player']['name'],
                                goals=stats['goals']['total'] or 0,
                                assists=stats['goals']['assists'] or 0
                            )
                        except Team.DoesNotExist:
                            continue

                self.stdout.write(self.style.SUCCESS("Zaktualizowano tabelę i strzelców."))

    @staticmethod
    def get_match_type_status(short):
        STATUS_MAP = {
            'TBD': 'Scheduled', 'NS': 'Scheduled',
            '1H': 'In Play', 'HT': 'In Play', '2H': 'In Play', 'ET': 'In Play',
            'BT': 'In Play', 'P': 'In Play', 'LIVE': 'In Play', 'SUSP': 'In Play', 'INT': 'In Play',
            'FT': 'Finished', 'AET': 'Finished', 'PEN': 'Finished',
            'PST': 'Postponed', 'CANC': 'Cancelled', 'ABD': 'Abandoned',
            'AWD': 'Not Played', 'WO': 'Not Played'
        }
        return STATUS_MAP.get(short, short)