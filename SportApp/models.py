from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass


class League(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    logo = models.URLField(null=True, blank=True)

    def __str__(self): return self.name


class Season(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    year = models.IntegerField()

    def __str__(self): return f"{self.league.name} {self.year}"


class Team(models.Model):
    name = models.CharField(max_length=100)
    league = models.ForeignKey(League, on_delete=models.CASCADE)  # Uproszczenie jest OK przy 1 sezonie
    logo = models.URLField(null=True, blank=True)

    def __str__(self): return self.name


# --- NOWOŚĆ: Model Zawodnika ---
class Player(models.Model):
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')

    def __str__(self): return self.name


class Match(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='matches')
    # Musimy użyć related_name, bo są dwa klucze do tego samego modelu (Team)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')

    date = models.DateTimeField()
    status_short = models.CharField(max_length=10, default="NS")  # NS, FT, HT
    status_long = models.CharField(max_length=50, default="Not Started")
    venue_name = models.CharField(max_length=100, null=True, blank=True)
    referee = models.CharField(max_length=100, null=True, blank=True)
    round = models.CharField(max_length=100, null=True, blank=True)

    # Wyniki
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)

    # --- STATYSTYKI GOSPODARZE ---
    home_shots_on_goal = models.IntegerField(null=True, blank=True)
    home_shots_off_goal = models.IntegerField(null=True, blank=True)
    home_total_shots = models.IntegerField(null=True, blank=True)
    home_blocked_shots = models.IntegerField(null=True, blank=True)
    home_fouls = models.IntegerField(null=True, blank=True)
    home_corners = models.IntegerField(null=True, blank=True)
    home_offsides = models.IntegerField(null=True, blank=True)
    home_possession = models.CharField(max_length=10, null=True, blank=True)  # Często API zwraca to jako "55%" (string)
    home_yellow_cards = models.IntegerField(null=True, blank=True)
    home_red_cards = models.IntegerField(null=True, blank=True)
    home_passes_total = models.IntegerField(null=True, blank=True)
    home_passes_accurate = models.IntegerField(null=True, blank=True)

    # --- STATYSTYKI GOŚCIE ---
    away_shots_on_goal = models.IntegerField(null=True, blank=True)
    away_shots_off_goal = models.IntegerField(null=True, blank=True)
    away_total_shots = models.IntegerField(null=True, blank=True)
    away_blocked_shots = models.IntegerField(null=True, blank=True)
    away_fouls = models.IntegerField(null=True, blank=True)
    away_corners = models.IntegerField(null=True, blank=True)
    away_offsides = models.IntegerField(null=True, blank=True)
    away_possession = models.CharField(max_length=10, null=True, blank=True)
    away_yellow_cards = models.IntegerField(null=True, blank=True)
    away_red_cards = models.IntegerField(null=True, blank=True)
    away_passes_total = models.IntegerField(null=True, blank=True)
    away_passes_accurate = models.IntegerField(null=True, blank=True)


class MatchAnalytics(models.Model):
    # Relacja OneToOne - jeden mecz ma jeden zestaw analiz
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='analytics')

    # Twoje wskaźniki
    indicator_1 = models.FloatField()
    indicator_2 = models.FloatField()
    indicator_3 = models.FloatField()
    indicator_4 = models.FloatField()

    # Kiedy wyliczono?
    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analiza meczu {self.match}"

class Standing(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    position = models.IntegerField()
    points = models.IntegerField()

    # Ogólne
    played = models.IntegerField()
    win = models.IntegerField()
    draw = models.IntegerField()
    lose = models.IntegerField()
    goals_for = models.IntegerField()
    goals_against = models.IntegerField()
    goals_diff = models.IntegerField()
    form = models.CharField(max_length=20, null=True, blank=True)  # np. "WWDLW"

    def __str__(self):
        return f"{self.position}. {self.team.name} ({self.points} pkt)"


class TopScorer(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    # Teraz łączymy się z modelem Player, a nie wpisujemy stringa
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    goals = models.IntegerField()


class MatchRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='ratings')
    rating = models.FloatField()

    class Meta:
        # Zabezpieczenie: Jeden user może ocenić jeden mecz tylko raz
        unique_together = ('user', 'match')
