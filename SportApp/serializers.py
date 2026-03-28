from django.db.models import Avg
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import User, League, Season, Team, Match, Standing, TopScorer, MatchRating, UserAnalytics
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .profiling import initialize_user_analytics

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class UserRadarChartSerializer(serializers.ModelSerializer):
    # To pole nie jest w bazie, tworzymy je dynamicznie
    chart_data = serializers.SerializerMethodField()
    profile_info = serializers.SerializerMethodField()

    class Meta:
        model = UserAnalytics
        fields = ('chart_data', 'profile_info')

    def get_profile_info(self, obj):
        """Zwraca nazwy profili do wyświetlenia nad wykresem"""
        return {
            "base_name": obj.base_football_profile,      # np. "Strateg"
            "current_name": obj.current_football_profile # np. "Agresor"
        }

    def get_chart_data(self, obj):
        """
        Formatuje dane idealnie pod bibliotekę 'Recharts' lub 'Chart.js'.
        Zwraca tablicę obiektów, gdzie każdy obiekt to jedna oś wykresu.
        """
        return [
            {
                "subject": "Hype",              # Nazwa osi
                "base": obj.base_hype,          # Wartość startowa (np. z ankiety)
                "current": obj.preference_hype, # Wartość aktualna (z ocen)
                "fullMark": 100                 # Skala (max)
            },
            {
                "subject": "Taktyka",
                "base": obj.base_tactical,
                "current": obj.preference_tactical,
                "fullMark": 100
            },
            {
                "subject": "Agresja",
                "base": obj.base_aggression,
                "current": obj.preference_aggression,
                "fullMark": 100
            },
            {
                "subject": "Defensywa",
                "base": obj.base_defense,
                "current": obj.preference_defense,
                "fullMark": 100
            }
        ]

class LeagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = League
        fields = '__all__'

class SeasonSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Season
        fields = ['id', 'name', 'year', 'is_current', 'league']

    @extend_schema_field(str)
    def get_name(self, obj):
        return str(obj)


class SeasonDetailSerializer(serializers.ModelSerializer):
    league_name = serializers.CharField(source='league.name', read_only=True)
    logo = serializers.URLField(source='league.logo', read_only=True)
    country = serializers.CharField(source='league.country', read_only=True)

    # Mapujemy 'year' z bazy na 'season_start_year' dla frontendu
    season_start_year = serializers.IntegerField(source='year', read_only=True)
    season_end_year = serializers.SerializerMethodField()

    class Meta:
        model = Season
        fields = ['league_name', 'logo', 'country', 'season_start_year', 'season_end_year']

    def get_season_end_year(self, obj):
        # Zakładamy, że sezon kończy się rok później (np. 2024 -> 2025)
        return obj.year + 1


class SearchResultSerializer(serializers.Serializer):
    name = serializers.CharField()
    type = serializers.CharField()
    logo = serializers.URLField()
    id = serializers.IntegerField(required=False)
    slug = serializers.CharField(required=False)

class TeamMatchSerializer(serializers.ModelSerializer):
    home_team = serializers.CharField(source='home_team.name', read_only=True)
    away_team = serializers.CharField(source='away_team.name', read_only=True)

    home_team_logo = serializers.URLField(source='home_team.logo', read_only=True)
    away_team_logo = serializers.URLField(source='away_team.logo', read_only=True)

    match_id = serializers.IntegerField(source='id', read_only=True)

    match_date = serializers.DateTimeField(source='date', read_only=True)

    home_score = serializers.IntegerField(read_only=True)
    away_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Match
        fields = [
            'match_id',
            'home_team', 'away_team',
            'home_team_logo', 'away_team_logo',
            'home_score', 'away_score',
            'match_date'
        ]


class TeamDetailSerializer(serializers.ModelSerializer):
    league_name = serializers.CharField(source='league.name', read_only=True)
    country = serializers.CharField(source='league.country', read_only=True)

    class Meta:
        model = Team
        fields = [
            'id',
            'name',
            'logo',
            'league',
            'league_name',
            'country',
            'venue_city',
            'venue_name',
            'venue_capacity',
            'founded'

        ]


from rest_framework import serializers
from .models import Standing


class BaseStandingSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    team_logo = serializers.URLField(source='team.logo', read_only=True)

    # Te pola zostaną wypełnione przez adnotacje w QuerySet (F expressions)
    # Dzięki temu nie potrzebujemy wolnego SerializerMethodField
    points = serializers.IntegerField(read_only=True)
    goals_diff = serializers.IntegerField(read_only=True)

    class Meta:
        model = Standing
        fields = [
            'position', 'team_name', 'team_logo', 'form',
            'played', 'win', 'draw', 'lose',
            'goals_for', 'goals_against', 'goals_diff', 'points'
        ]


# Serializery Home/Away mapują specyficzne pola (np. home_win) na ogólne nazwy (win)
# aby frontend otrzymywał zawsze taką samą strukturę JSON.

class HomeStandingSerializer(BaseStandingSerializer):
    played = serializers.IntegerField(source='home_played', read_only=True)
    win = serializers.IntegerField(source='home_win', read_only=True)

    points = serializers.IntegerField(source='calculated_points', read_only=True)
    goals_diff = serializers.IntegerField(source='calculated_diff', read_only=True)

    draw = serializers.IntegerField(source='home_draw', read_only=True)
    lose = serializers.IntegerField(source='home_lose', read_only=True)
    goals_for = serializers.IntegerField(source='home_goals_for', read_only=True)
    goals_against = serializers.IntegerField(source='home_goals_against', read_only=True)


class AwayStandingSerializer(BaseStandingSerializer):
    played = serializers.IntegerField(source='away_played', read_only=True)
    win = serializers.IntegerField(source='away_win', read_only=True)

    points = serializers.IntegerField(source='calculated_points', read_only=True)
    goals_diff = serializers.IntegerField(source='calculated_diff', read_only=True)

    draw = serializers.IntegerField(source='away_draw', read_only=True)
    lose = serializers.IntegerField(source='away_lose', read_only=True)
    goals_for = serializers.IntegerField(source='away_goals_for', read_only=True)
    goals_against = serializers.IntegerField(source='away_goals_against', read_only=True)


class StandingSerializer(BaseStandingSerializer):
    pass


class TopScorerSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)

    total_points = serializers.IntegerField(read_only=True)

    class Meta:
        model = TopScorer
        fields = '__all__'


class MatchBaseSerializer(serializers.ModelSerializer):
    match_id = serializers.IntegerField(source='api_id', read_only=True)  # Zmienione na api_id (bo tak masz w modelu)
    match_date = serializers.DateTimeField(source='date', read_only=True)

    home_team = serializers.CharField(source='home_team.name', read_only=True)
    away_team = serializers.CharField(source='away_team.name', read_only=True)
    home_team_logo = serializers.URLField(source='home_team.logo', read_only=True)
    away_team_logo = serializers.URLField(source='away_team.logo', read_only=True)
    league_name = serializers.CharField(source='season.league.name', read_only=True)

    season = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    # Status masz w modelu jako 'status', venue_name też jest w modelu Match
    venue_name = serializers.CharField(read_only=True)

    class Meta:
        model = Match
        fields = [
            'match_id', 'match_date', 'league_name', 'season',
            'home_team', 'away_team', 'home_team_logo', 'away_team_logo',
            'home_score', 'away_score',
            'status', 'venue_name', 'round',
            'average_rating'
        ]

    def get_season(self, obj):
        if obj.season:
            return f"{obj.season.year}/{obj.season.year + 1}"
        return ""

    @extend_schema_field(float)
    def get_average_rating(self, obj):
        if hasattr(obj, 'avg_rating'):
            return round(obj.avg_rating, 2) if obj.avg_rating else 0.0

        avg = obj.ratings.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 2) if avg else 0.0


# --- 2. LIST SERIALIZER ---
class MatchListSerializer(MatchBaseSerializer):
    defense_score = serializers.FloatField(source='analytics.defense_score', read_only=True, allow_null=True)
    hype_score = serializers.FloatField(source='analytics.hype_score', read_only=True, allow_null=True)
    tactical_score = serializers.FloatField(source='analytics.tactical_score', read_only=True, allow_null=True)
    aggression_score = serializers.FloatField(source='analytics.aggression_score', read_only=True, allow_null=True)

    class Meta(MatchBaseSerializer.Meta):
        fields = MatchBaseSerializer.Meta.fields + [
            'defense_score', 'hype_score', 'tactical_score', 'aggression_score'
        ]


# --- 3. DETAIL SERIALIZER (NAPRAWIONY) ---
class MatchDetailSerializer(MatchBaseSerializer):
    # Pojemność bierzemy z modelu Team (bo w Match go nie ma)
    capacity = serializers.IntegerField(source='home_team.venue_capacity', read_only=True)

    # --- MAPOWANIE PÓL (To naprawia błąd ImproperlyConfigured) ---
    # Lewa strona = nazwa w JSON (frontend), Prawa strona (source) = nazwa w Twoim Modelu

    # HOME TEAM
    home_team_shots_on_goal = serializers.IntegerField(source='home_shots_on_goal', read_only=True)
    home_team_shots_off_goal = serializers.IntegerField(source='home_shots_off_goal', read_only=True)
    home_team_total_shots = serializers.IntegerField(source='home_total_shots', read_only=True)
    home_team_blocked_shots = serializers.IntegerField(source='home_blocked_shots', read_only=True)
    home_team_shots_insidebox = serializers.IntegerField(source='home_shots_inside_box', read_only=True)
    home_team_shots_outsidebox = serializers.IntegerField(source='home_shots_outside_box', read_only=True)
    home_team_fouls = serializers.IntegerField(source='home_fouls', read_only=True)
    home_team_corner_kicks = serializers.IntegerField(source='home_corners', read_only=True)
    home_team_offsides = serializers.IntegerField(source='home_offsides', read_only=True)
    home_team_ball_possession = serializers.CharField(source='home_possession', read_only=True)
    home_team_yellow_cards = serializers.IntegerField(source='home_yellow_cards', read_only=True)
    home_team_red_cards = serializers.IntegerField(source='home_red_cards', read_only=True)
    home_team_goalkeeper_saves = serializers.IntegerField(source='home_goalkeeper_saves', read_only=True)
    home_team_total_passes = serializers.IntegerField(source='home_passes_total', read_only=True)
    home_team_passes_accuracy = serializers.IntegerField(source='home_passes_accurate', read_only=True)

    # AWAY TEAM
    away_team_shots_on_goal = serializers.IntegerField(source='away_shots_on_goal', read_only=True)
    away_team_shots_off_goal = serializers.IntegerField(source='away_shots_off_goal', read_only=True)
    away_team_total_shots = serializers.IntegerField(source='away_total_shots', read_only=True)
    away_team_blocked_shots = serializers.IntegerField(source='away_blocked_shots', read_only=True)
    away_team_shots_insidebox = serializers.IntegerField(source='away_shots_inside_box', read_only=True)
    away_team_shots_outsidebox = serializers.IntegerField(source='away_shots_outside_box', read_only=True)
    away_team_fouls = serializers.IntegerField(source='away_fouls', read_only=True)
    away_team_corner_kicks = serializers.IntegerField(source='away_corners', read_only=True)
    away_team_offsides = serializers.IntegerField(source='away_offsides', read_only=True)
    away_team_ball_possession = serializers.CharField(source='away_possession', read_only=True)
    away_team_yellow_cards = serializers.IntegerField(source='away_yellow_cards', read_only=True)
    away_team_red_cards = serializers.IntegerField(source='away_red_cards', read_only=True)
    away_team_goalkeeper_saves = serializers.IntegerField(source='away_goalkeeper_saves', read_only=True)
    away_team_total_passes = serializers.IntegerField(source='away_passes_total', read_only=True)
    away_team_passes_accuracy = serializers.IntegerField(source='away_passes_accurate', read_only=True)

    class Meta(MatchBaseSerializer.Meta):
        fields = MatchBaseSerializer.Meta.fields + [
            'capacity', 'referee',
            # Home
            'home_team_shots_on_goal', 'home_team_shots_off_goal', 'home_team_total_shots',
            'home_team_blocked_shots', 'home_team_shots_insidebox', 'home_team_shots_outsidebox',
            'home_team_fouls', 'home_team_corner_kicks', 'home_team_offsides',
            'home_team_ball_possession', 'home_team_yellow_cards', 'home_team_red_cards',
            'home_team_goalkeeper_saves', 'home_team_total_passes', 'home_team_passes_accuracy',
            # Away
            'away_team_shots_on_goal', 'away_team_shots_off_goal', 'away_team_total_shots',
            'away_team_blocked_shots', 'away_team_shots_insidebox', 'away_team_shots_outsidebox',
            'away_team_fouls', 'away_team_corner_kicks', 'away_team_offsides',
            'away_team_ball_possession', 'away_team_yellow_cards', 'away_team_red_cards',
            'away_team_goalkeeper_saves', 'away_team_total_passes', 'away_team_passes_accuracy',
        ]


# --- 4. SCORE SERIALIZER ---
class MatchScoreSerializer(MatchListSerializer):
    calculated_at = serializers.DateTimeField(source='analytics.calculated_at', read_only=True, allow_null=True)

    class Meta(MatchListSerializer.Meta):
        fields = MatchListSerializer.Meta.fields + ['calculated_at']


# --- 5. RATING SERIALIZER ---
class MatchRatingSerializer(serializers.ModelSerializer):
    # 1. MATCH: Lookup po api_id
    match = serializers.SlugRelatedField(
        slug_field='api_id',
        queryset=Match.objects.all()
    )

    # 2. USER: Jawnie ustawiamy jako read_only.
    # Dzięki temu walidator nie krzyczy, że brakuje tego pola w request.data
    user = serializers.StringRelatedField(read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = MatchRating
        # Pamiętaj, aby dodać 'user_name' do pól, a usunąć stare 'username' jeśli tam było
        fields = ['id', 'match', 'user', 'user_name', 'rating', 'created_at']  # ewentualnie 'comment'
        read_only_fields = ['id', 'created_at', 'user']

    # Ta metoda generuje zawartość pola 'user_name'
    def get_user_name(self, obj):
        # Pobieramy imię i nazwisko
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()

        # Jeśli użytkownik ma wpisane imię i nazwisko, zwracamy je.
        if full_name:
            return full_name

        # Jeśli nie ma imienia/nazwiska, zwracamy email lub username jako awaryjne rozwiązanie
        return obj.user.username  # lub obj.user.email


class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    # --- 1. DEFINIUJEMY POLA DODATKOWE (KTÓRYCH NIE MA W TABELI USER) ---
    # write_only=True: Przyjmujemy dane, ale ich nie odsyłamy
    # required=False: Żeby nie blokować rejestracji, jeśli frontend ich nie wyśle (obsłużymy to domyślnie)
    personality_type = serializers.CharField(write_only=True, required=False)
    football_profile = serializers.CharField(write_only=True, required=False)

    base_hype = serializers.FloatField(write_only=True, required=False)
    base_tactical = serializers.FloatField(write_only=True, required=False)
    base_aggression = serializers.FloatField(write_only=True, required=False)
    base_defense = serializers.FloatField(write_only=True, required=False)

    class Meta:
        model = User
        # Wymieniamy wszystkie pola, które chcemy przepuścić przez API
        fields = (
            'username', 'email', 'password', 'confirm_password',
            'first_name', 'last_name',
            'personality_type', 'football_profile',
            'base_hype', 'base_tactical', 'base_aggression', 'base_defense'
        )
        extra_kwargs = {
            'username': {'required': False}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Hasła nie są identyczne."})
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ten adres email jest już zajęty.")
        return value

    def create(self, validated_data):
        # 1. Usuwamy pola dodatkowe (niezwiązane z modelem User)
        validated_data.pop('confirm_password', None)
        validated_data.pop('personality_type', None)
        validated_data.pop('football_profile', None)
        validated_data.pop('base_hype', None)
        validated_data.pop('base_tactical', None)
        validated_data.pop('base_aggression', None)
        validated_data.pop('base_defense', None)

        # 2. Wyciągamy kluczowe pola dla create_user, usuwając je ze słownika
        # Dzięki .pop() wyciągamy wartość i jednocześnie czyścimy validated_data
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # Pobieramy username lub używamy emaila, jeśli go nie ma
        username = validated_data.pop('username', email)

        # 3. Tworzymy użytkownika
        # W validated_data zostały teraz tylko first_name i last_name (i ewentualnie inne pola modelu)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            **validated_data  # Teraz nie ma tu już 'email' ani 'username', więc nie ma konfliktu
        )

        # 4. Przypisanie do grupy
        try:
            user_group = Group.objects.get(name='User')
            user.groups.add(user_group)
        except Group.DoesNotExist:
            pass

        return user


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Wskazujemy, że polem wejściowym jest email, nie username
    username_field = User.EMAIL_FIELD

    def validate(self, attrs):
        # Pobieramy email i hasło z requestu
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Szukamy użytkownika po emailu
            user = User.objects.filter(email=email).first()

            if user and user.check_password(password):
                # Jeśli użytkownik istnieje i hasło jest poprawne:
                if not user.is_active:
                    raise serializers.ValidationError({"detail": "Konto jest nieaktywne."})

                # Generujemy tokeny dla tego użytkownika
                refresh = self.get_token(user)

                data = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                }

                return data
            else:
                raise serializers.ValidationError({"detail": "Nieprawidłowy email lub hasło."})
        else:
            raise serializers.ValidationError({"detail": "Email i hasło są wymagane."})

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Kodujemy dane wewnątrz Tokena (claims)
        token['firstName'] = user.first_name
        token['lastName'] = user.last_name

        # --- ZMIANA 1: Dodajemy flagę is_superuser ---
        token['is_superuser'] = user.is_superuser

        # --- ZMIANA 2: Logika roli ---
        # Warto, aby superuser automatycznie miał też rolę 'admin',
        # nawet jeśli zapomniałeś dodać go do grupy "Admin".
        if user.is_superuser or user.groups.filter(name='Admin').exists():
            token['role'] = 'admin'
        else:
            token['role'] = 'user'

        return token

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.refresh_token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.refresh_token).blacklist()
        except TokenError:

            pass


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Stare hasło jest nieprawidłowe.")
        return value


class TeamSimpleSerializer(serializers.ModelSerializer):
    """Uproszczony serializer drużyny (używany w rekomendacjach)"""

    class Meta:
        model = Team
        fields = ['id', 'name', 'logo']


class MatchAnalyticsSimpleSerializer(serializers.ModelSerializer):
    """Uproszczony serializer statystyk (tylko główne wskaźniki)"""

    class Meta:
        model = Match
        # Tutaj musisz uważać - w modelu Match nie masz tych pól bezpośrednio,
        # ale w widoku rekomendacji odnosimy się do obiektu MatchAnalytics.
        # Dlatego lepiej zrobić to tak:
        fields = []  # Placeholder, w praktyce użyjemy zagnieżdżenia


# Właściwy serializer dla modelu MatchAnalytics
from .models import MatchAnalytics  # Upewnij się, że masz import


class AnalyticsScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchAnalytics
        fields = ['hype_score', 'tactical_score', 'aggression_score', 'defense_score']


class PersonalizedMatchSerializer(serializers.ModelSerializer):
    """
    Serializer zwracający mecz wraz z wynikiem dopasowania (match_score).
    ZMIANA: Pole 'id' zwraca teraz 'api_id'.
    """
    # --- TU JEST ZMIANA ---
    # Nadpisujemy pole 'id'. Source='api_id' mówi Django:
    # "Weź wartość z kolumny api_id, ale w JSON nazwij to po prostu id"
    id = serializers.IntegerField(source='api_id', read_only=True)

    home_team = TeamSimpleSerializer(read_only=True)
    away_team = TeamSimpleSerializer(read_only=True)
    analytics = AnalyticsScoreSerializer(read_only=True)

    match_score = serializers.FloatField(read_only=True)

    league_name = serializers.CharField(source='season.league.name', read_only=True)
    league_logo = serializers.URLField(source='season.league.logo', read_only=True)

    class Meta:
        model = Match
        fields = [
            'id',  # To pole teraz zawiera api_id
            'date',
            'home_team',
            'away_team',
            'league_name',
            'league_logo',
            'status',
            'analytics',
            'match_score'
        ]