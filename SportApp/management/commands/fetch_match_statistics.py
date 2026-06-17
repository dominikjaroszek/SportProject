import logging
import os
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from SportApp.models import Match
from SportApp.services import FootballAPIService
from django.utils import timezone

LOG_FILE_PATH = os.path.join(settings.BASE_DIR, 'match_updates.log')
logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class Command(BaseCommand):
    help = 'Pobiera brakujące statystyki dla zakończonych meczów i loguje do pliku'

    def handle(self, *args, **options):
        service = FootballAPIService()
        teraz = timezone.now()

        matches_to_update = Match.objects.filter(
            status="Finished",
            home_total_shots__isnull=True,
            home_score__isnull=False,
            away_score__isnull=False,
            date__lte=teraz
        ).order_by('-date')[:60]

        total_count = len(matches_to_update)
        msg_start = f"Rozpoczęto aktualizację. Znaleziono {total_count} meczów."

        self.stdout.write(msg_start)
        logging.info(msg_start)

        for i, match in enumerate(matches_to_update):
            match_info = f"{match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}"
            current_log = f"[{i + 1}/{total_count}] Przetwarzanie: {match_info} (API ID: {match.api_id})"

            self.stdout.write(self.style.HTTP_INFO(current_log))
            logging.info(current_log)

            try:
                stats_data = service.get_fixture_statistics(match.api_id)

                if not stats_data:
                    warn_msg = f"Brak statystyk w API dla meczu {match.api_id}"
                    self.stdout.write(self.style.WARNING(f"   --> {warn_msg}"))
                    logging.warning(warn_msg)
                    time.sleep(1)
                    continue

                for item in stats_data:
                    team_id = item['team']['id']
                    stats_list = item['statistics']
                    prefix = 'home_' if team_id == match.home_team.api_id else 'away_'

                    for stat in stats_list:
                        stat_type = stat['type']
                        stat_value = 0 if stat['value'] is None else stat['value']

                        mapping = {
                            'Shots on Goal': 'shots_on_goal',
                            'Shots off Goal': 'shots_off_goal',
                            'Total Shots': 'total_shots',
                            'Blocked Shots': 'blocked_shots',
                            'Fouls': 'fouls',
                            'Corner Kicks': 'corners',
                            'Offsides': 'offsides',
                            'Yellow Cards': 'yellow_cards',
                            'Red Cards': 'red_cards',
                            'Total passes': 'passes_total',
                            'Passes accurate': 'passes_accurate',
                            'Goalkeeper saves': 'goalkeeper_saves',
                            'Shots insidebox': 'shots_inside_box',
                            'Shots outsidebox': 'shots_outside_box',
                        }

                        if stat_type in mapping:
                            setattr(match, f"{prefix}{mapping[stat_type]}", stat_value)
                        elif stat_type == 'Ball Possession':
                            setattr(match, f"{prefix}possession", str(stat_value))

                match.save()
                success_msg = f"Zapisano statystyki dla meczu ID {match.api_id}"
                self.stdout.write(self.style.SUCCESS(f"   --> {success_msg}"))
                logging.info(success_msg)

            except Exception as e:
                err_msg = f"Błąd podczas przetwarzania meczu {match.api_id}: {str(e)}"
                self.stdout.write(self.style.ERROR(err_msg))
                logging.error(err_msg)

            time.sleep(7)

        final_msg = "Zakończono sesję aktualizacji statystyk."
        self.stdout.write(self.style.SUCCESS(f"\n{final_msg}"))
        logging.info(final_msg)