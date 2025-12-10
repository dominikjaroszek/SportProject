# SportApp/analytics.py
from django.db.models import Q
from .models import Match, MatchAnalytics


class MatchAnalyzer:
    def __init__(self):
        # KONFIGURACJA LIMITÓW (BENCHMARKS)
        self.LIMITS = {
            'DEFENSE': 25.0,  # Iron Curtain
            'TACTICAL': 225.0,  # Indicator 3
            'HYPE': 70.0,  # Adrenaline
            'AGGRESSION': 95.0  # War Zone
        }
        self.WEIGHTS = [5, 4, 3, 2, 1]

    def _get_team_stat_in_match(self, match, team_id, stat_name):
        """
        Pomocnicza funkcja: Pobiera statystykę dla konkretnej drużyny w meczu,
        sprawdzając czy była ona gospodarzem czy gościem.
        """
        prefix = ""
        if match.home_team.id == team_id:
            prefix = "home_"
        elif match.away_team.id == team_id:
            prefix = "away_"
        else:
            return 0

        field_map = {
            'blocked_shots': f'{prefix}blocked_shots',
            'goalkeeper_saves': f'{prefix}goalkeeper_saves',
            'pass_percent': f'{prefix}passes_accurate',
            'offsides': f'{prefix}offsides',
            'shots_inside_box': f'{prefix}shots_inside_box',
            'corner_kicks': f'{prefix}corners',
            'shots_on_goal': f'{prefix}shots_on_goal',
            'fouls': f'{prefix}fouls',
            'yellow_cards': f'{prefix}yellow_cards',
            'red_cards': f'{prefix}red_cards',
        }

        field_name = field_map.get(stat_name)
        val = getattr(match, field_name, 0)

        return val if val is not None else 0

    def _get_weighted_stat(self, matches_list, team_id, stat_key):
        weighted_sum = 0
        current_weight_sum = 0

        # Bierzemy max 5 ostatnich meczów
        for i, match in enumerate(matches_list[:5]):
            weight = self.WEIGHTS[i]
            val = self._get_team_stat_in_match(match, team_id, stat_key)

            weighted_sum += val * weight
            current_weight_sum += weight

        if current_weight_sum == 0: return 0
        return weighted_sum / current_weight_sum

    def _normalize(self, raw_value, max_limit):
        percent = (raw_value / max_limit) * 100
        return min(round(percent), 100)

    def calculate_match_analytics(self, match_obj):
        """
        Główna metoda wywoływana dla konkretnego meczu (match_obj).
        """
        # 1. Pobierz 5 ostatnich ZAKOŃCZONYCH meczów dla Gospodarza i Gościa
        # Wykluczamy ten mecz, który właśnie analizujemy (jeśli już się odbył)
        home_last_5 = Match.objects.filter(
            (Q(home_team=match_obj.home_team) | Q(away_team=match_obj.home_team)),
            status='Finished',
            date__lt=match_obj.date  # Tylko mecze sprzed daty tego meczu
        ).order_by('-date')[:5]

        away_last_5 = Match.objects.filter(
            (Q(home_team=match_obj.away_team) | Q(away_team=match_obj.away_team)),
            status='Finished',
            date__lt=match_obj.date
        ).order_by('-date')[:5]

        if not home_last_5 or not away_last_5:
            return None

        metrics = [
            'blocked_shots', 'pass_percent', 'offsides', 'goalkeeper_saves',
            'shots_inside_box', 'corner_kicks', 'shots_on_goal',
            'fouls', 'yellow_cards', 'red_cards'
        ]

        h_stats = {k: self._get_weighted_stat(home_last_5, match_obj.home_team.id, k) for k in metrics}
        a_stats = {k: self._get_weighted_stat(away_last_5, match_obj.away_team.id, k) for k in metrics}

        raw_defense = (h_stats['blocked_shots'] + a_stats['blocked_shots']) + \
                      (h_stats['goalkeeper_saves'] + a_stats['goalkeeper_saves'])

        raw_tactical = ((h_stats['pass_percent'] + a_stats['pass_percent']) / 5) + \
                       ((h_stats['offsides'] + a_stats['offsides']) * 5)

        raw_hype = ((h_stats['shots_inside_box'] + a_stats['shots_inside_box']) * 2) + \
                   (h_stats['corner_kicks'] + a_stats['corner_kicks']) + \
                   (h_stats['shots_on_goal'] + a_stats['shots_on_goal'])

        raw_aggression = (h_stats['fouls'] + a_stats['fouls']) + \
                         ((h_stats['yellow_cards'] + a_stats['yellow_cards']) * 5) + \
                         ((h_stats['red_cards'] + a_stats['red_cards']) * 20)

        analytics, created = MatchAnalytics.objects.update_or_create(
            match=match_obj,
            defaults={
                'defense_score': self._normalize(raw_defense, self.LIMITS['DEFENSE']),
                'tactical_score': self._normalize(raw_tactical, self.LIMITS['TACTICAL']),
                'hype_score': self._normalize(raw_hype, self.LIMITS['HYPE']),
                'aggression_score': self._normalize(raw_aggression, self.LIMITS['AGGRESSION'])
            }
        )
        return analytics