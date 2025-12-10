from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass


class League(models.Model):
    api_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    logo = models.URLField(null=True, blank=True)

    def __str__(self): return self.name


class Season(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    year = models.IntegerField()
    is_current = models.BooleanField(default=False)

    @property
    def display_year(self):

        return f"{self.year}/{self.year + 1}"

    class Meta:
        unique_together = ('league', 'year')

    def __str__(self): return f"{self.league.name} {self.year}"


class Team(models.Model):
    api_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='teams', null=True)

    logo = models.URLField(null=True, blank=True)
    founded = models.IntegerField(null=True, blank=True)
    venue_name = models.CharField(max_length=100, null=True, blank=True)
    venue_city = models.CharField(max_length=100, null=True, blank=True)
    venue_capacity = models.IntegerField(null=True, blank=True)

    def __str__(self): return self.name


class Match(models.Model):
    api_id = models.IntegerField(unique=True)

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='matches')
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')

    date = models.DateTimeField()
    status = models.CharField(max_length=50, default="Not Started")

    venue_name = models.CharField(max_length=100, null=True, blank=True)
    referee = models.CharField(max_length=100, null=True, blank=True)
    round = models.CharField(max_length=100, null=True, blank=True)


    home_score = models.IntegerField(null=True, blank=True)
    home_shots_on_goal = models.IntegerField(null=True, blank=True)
    home_shots_off_goal = models.IntegerField(null=True, blank=True)
    home_total_shots = models.IntegerField(null=True, blank=True)
    home_shots_inside_box = models.IntegerField(null=True, blank=True)
    home_shots_outside_box = models.IntegerField(null=True, blank=True)
    home_blocked_shots = models.IntegerField(null=True, blank=True)
    home_fouls = models.IntegerField(null=True, blank=True)
    home_corners = models.IntegerField(null=True, blank=True)
    home_offsides = models.IntegerField(null=True, blank=True)
    home_possession = models.CharField(max_length=10, null=True, blank=True)
    home_yellow_cards = models.IntegerField(null=True, blank=True)
    home_red_cards = models.IntegerField(null=True, blank=True)
    home_passes_total = models.IntegerField(null=True, blank=True)
    home_passes_accurate = models.IntegerField(null=True, blank=True)
    home_goalkeeper_saves = models.IntegerField(null=True, blank=True)

    away_score = models.IntegerField(null=True, blank=True)
    away_shots_on_goal = models.IntegerField(null=True, blank=True)
    away_shots_off_goal = models.IntegerField(null=True, blank=True)
    away_total_shots = models.IntegerField(null=True, blank=True)
    away_blocked_shots = models.IntegerField(null=True, blank=True)
    away_shots_inside_box = models.IntegerField(null=True, blank=True)
    away_shots_outside_box = models.IntegerField(null=True, blank=True)
    away_fouls = models.IntegerField(null=True, blank=True)
    away_corners = models.IntegerField(null=True, blank=True)
    away_offsides = models.IntegerField(null=True, blank=True)
    away_possession = models.CharField(max_length=10, null=True, blank=True)
    away_yellow_cards = models.IntegerField(null=True, blank=True)
    away_red_cards = models.IntegerField(null=True, blank=True)
    away_passes_total = models.IntegerField(null=True, blank=True)
    away_passes_accurate = models.IntegerField(null=True, blank=True)
    away_goalkeeper_saves = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Matches"
        ordering = ['date']  # Domyślne sortowanie po dacie

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"


class MatchAnalytics(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='analytics')
    defense_score = models.FloatField()
    hype_score = models.FloatField()
    tactical_score = models.FloatField()
    aggression_score = models.FloatField()
    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analiza meczu {self.match}"

class Standing(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    position = models.IntegerField()
    points = models.IntegerField()
    form = models.CharField(max_length=20, null=True, blank=True)

    status = models.CharField(max_length=100)
    last_update = models.DateTimeField()

    played = models.IntegerField(default=0)
    win = models.IntegerField(default=0)
    draw = models.IntegerField(default=0)
    lose = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)
    goals_diff = models.IntegerField(default=0)

    home_played = models.IntegerField(default=0)
    home_win = models.IntegerField(default=0)
    home_draw = models.IntegerField(default=0)
    home_lose = models.IntegerField(default=0)
    home_goals_for = models.IntegerField(default=0)
    home_goals_against = models.IntegerField(default=0)

    away_played = models.IntegerField(default=0)
    away_win = models.IntegerField(default=0)
    away_draw = models.IntegerField(default=0)
    away_lose = models.IntegerField(default=0)
    away_goals_for = models.IntegerField(default=0)
    away_goals_against = models.IntegerField(default=0)

    class Meta:
        unique_together = ('season', 'team')
        ordering = ['position']

    def __str__(self):
        return f"{self.position}. {self.team.name}"


class TopScorer(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    player_name = models.CharField(max_length=100)

    player_api_id = models.IntegerField(null=True, blank=True)

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    goals = models.IntegerField()
    assists = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-goals']

    def __str__(self):
        return f"{self.player_name} ({self.goals})"


class MatchRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='ratings')
    rating = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'match')