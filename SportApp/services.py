import requests
import time
from django.conf import settings

class FootballAPIService:
    BASE_URL = "https://v3.football.api-sports.io"

    def __init__(self):
        self.headers = {
            "x-rapidapi-key": settings.API_FOOTBALL_KEY,
            "x-rapidapi-host": settings.API_FOOTBALL_HOST
        }

    def _get(self, endpoint, params):
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            time.sleep(7)
            return response.json().get('response', [])
        except requests.RequestException as e:
            print(f"Błąd API ({endpoint}): {e}")
            return []

    def get_league_info(self, league_id):
        return self._get("leagues", {'id': league_id})

    def get_teams(self, league_id, season):
        return self._get("teams", {'league': league_id, 'season': season})

    def get_standings(self, league_id, season):
        return self._get("standings", {'league': league_id, 'season': season})

    def get_fixtures(self, league_id, season):
        return self._get("fixtures", {'league': league_id, 'season': season})

    def get_top_scorers(self, league_id, season):
        return self._get("players/topscorers", {'league': league_id, 'season': season})

    def get_fixture_statistics(self, fixture_id):
        return self._get("fixtures/statistics", {'fixture': fixture_id})