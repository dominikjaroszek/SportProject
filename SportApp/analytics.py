from django.db.models import Q
from .models import Match, MatchAnalytics, AnalyticsBenchmark


class MatchAnalyzer:
    def __init__(self):
        self.STAT_CAPS = {
            'blocked_shots': 8.0,
            'offsides': 5.0,
            'passes_total': 800.0,
            'passes_accurate': 90.0,
            'shots_inside_box': 12.0,
            'corners': 12.0,
            'shots_on_goal': 10.0,
            'fouls': 20.0,
            'yellow_cards': 4.0,
            'red_cards': 1.0
        }

        self._load_stat_caps()
        self.MAX_SCORES = self._calculate_max_possible_scores()
        self.WEIGHTS = [5, 4, 3, 2, 1]

    def _load_stat_caps(self):

        try:
            benchmarks = AnalyticsBenchmark.objects.all()
            for b in benchmarks:
                # Usuwamy prefix 'limit_', jeśli istnieje (zależnie jak zapisała komenda)
                key = b.stat_name.replace('limit_', '')

                if b.benchmark_value > 0:
                    self.STAT_CAPS[key] = b.benchmark_value
        except Exception as e:
            print(f"Warning: Nie udało się załadować benchmarków: {e}")

    def _calculate_max_possible_scores(self):

        caps = self.STAT_CAPS
        max_defense = (caps['blocked_shots'] * 2) + ((caps['offsides'] * 3) * 2)
        max_tactical = ((caps['passes_accurate'] * 2) / 5) + ((caps['passes_total'] * 2) / 20)

        max_hype = ((caps['shots_inside_box'] * 2) * 2) + \
                   (caps['corners'] * 2) + \
                   (caps['shots_on_goal'] * 2)

        max_aggression = (caps['fouls'] * 2) + \
                         ((caps['yellow_cards'] * 5) * 2) + \
                         ((caps['red_cards'] * 20) * 2)

        return {
            'DEFENSE': max_defense,
            'TACTICAL': max_tactical,
            'HYPE': max_hype,
            'AGGRESSION': max_aggression
        }

    def _get_team_stat_in_match(self, match, team_id, stat_name):
        prefix = ""
        if match.home_team.id == team_id:
            prefix = "home_"
        elif match.away_team.id == team_id:
            prefix = "away_"
        else:
            return 0

        field_map = {
            'blocked_shots': f'{prefix}blocked_shots',
            'passes_total': f'{prefix}passes_total',
            'passes_accurate': f'{prefix}passes_accurate',
            'offsides': f'{prefix}offsides',
            'shots_inside_box': f'{prefix}shots_inside_box',
            'corners': f'{prefix}corners',
            'shots_on_goal': f'{prefix}shots_on_goal',
            'fouls': f'{prefix}fouls',
            'yellow_cards': f'{prefix}yellow_cards',
            'red_cards': f'{prefix}red_cards',
        }

        field_name = field_map.get(stat_name)
        val = getattr(match, field_name, 0)
        return val if val is not None else 0

    def _get_capped_weighted_stat(self, matches_list, team_id, stat_key):

        weighted_sum = 0
        current_weight_sum = 0

        limit = self.STAT_CAPS.get(stat_key, 99999.0)

        for i, match in enumerate(matches_list[:5]):
            weight = self.WEIGHTS[i]
            raw_val = self._get_team_stat_in_match(match, team_id, stat_key)
            capped_val = min(raw_val, limit)
            weighted_sum += capped_val * weight
            current_weight_sum += weight

        if current_weight_sum == 0: return 0
        return weighted_sum / current_weight_sum

    def _normalize(self, raw_value, max_limit):
        if max_limit == 0: return 0
        percent = (raw_value / max_limit) * 100
        return min(round(percent), 100)

    def calculate_match_analytics(self, match_obj):
        home_last_5 = Match.objects.filter(
            (Q(home_team=match_obj.home_team) | Q(away_team=match_obj.home_team)),
            status='Finished',
            date__lt=match_obj.date
        ).order_by('-date')[:5]

        away_last_5 = Match.objects.filter(
            (Q(home_team=match_obj.away_team) | Q(away_team=match_obj.away_team)),
            status='Finished',
            date__lt=match_obj.date
        ).order_by('-date')[:5]

        if not home_last_5 or not away_last_5:
            return None

        metrics = [
            'blocked_shots', 'passes_total', 'passes_accurate', 'offsides',
            'shots_inside_box', 'corners', 'shots_on_goal',
            'fouls', 'yellow_cards', 'red_cards'
        ]

        h = {k: self._get_capped_weighted_stat(home_last_5, match_obj.home_team.id, k) for k in metrics}
        a = {k: self._get_capped_weighted_stat(away_last_5, match_obj.away_team.id, k) for k in metrics}

        raw_defense = (h['blocked_shots'] + a['blocked_shots']) + \
                      ((h['offsides'] + a['offsides']) * 3)

        raw_tactical = ((h['passes_accurate'] + a['passes_accurate']) / 5) + \
                       ((h['passes_total'] + a['passes_total']) / 20)

        raw_hype = ((h['shots_inside_box'] + a['shots_inside_box']) * 2) + \
                   (h['corners'] + a['corners']) + \
                   (h['shots_on_goal'] + a['shots_on_goal'])

        raw_aggression = (h['fouls'] + a['fouls']) + \
                         ((h['yellow_cards'] + a['yellow_cards']) * 5) + \
                         ((h['red_cards'] + a['red_cards']) * 20)

        analytics, created = MatchAnalytics.objects.update_or_create(
            match=match_obj,
            defaults={
                'defense_score': self._normalize(raw_defense, self.MAX_SCORES['DEFENSE']),
                'tactical_score': self._normalize(raw_tactical, self.MAX_SCORES['TACTICAL']),
                'hype_score': self._normalize(raw_hype, self.MAX_SCORES['HYPE']),
                'aggression_score': self._normalize(raw_aggression, self.MAX_SCORES['AGGRESSION'])
            }
        )
        return analytics