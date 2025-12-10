from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from .models import User, League, Season, Team, Match, Standing, TopScorer, MatchRating

# 1. USER
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Nigdy nie zwracaj hasła (password) w API!
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


# 2. LIGA
class LeagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = League
        fields = '__all__'


# 3. SEZON
# serializers.py

class SeasonSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Season
        fields = ['id', 'name', 'year', 'is_current', 'league']

    @extend_schema_field(str)
    def get_name(self, obj):
        return str(obj)


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'logo', 'league', 'venue_city'] # Dodałem 'league'

# 6. MECZ (Najważniejszy!)
class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = '__all__'
        # Trik dla Reacta: depth = 1
        # Dzięki temu zamiast "home_team": 5, dostaniesz pełny obiekt:
        # "home_team": { "id": 5, "name": "Real Madryt", "logo": "..." }
        # To oszczędza mnóstwo zapytań do API!

    # Jeśli potrzebujesz osobnego serializera do TWORZENIA meczu (gdzie podajesz tylko ID),


# to zazwyczaj tworzy się osobny "MatchCreateSerializer" bez depth=1.
# Ale na start ten powyżej wystarczy (przy zapisie Django DRF jest sprytne i obsłuży ID).

# 7. TABELA
class StandingSerializer(serializers.ModelSerializer):
    # Chcemy widzieć nazwę drużyny w tabeli
    team_name = serializers.CharField(source='team.name', read_only=True)
    team_logo = serializers.URLField(source='team.logo', read_only=True)

    class Meta:
        model = Standing
        fields = '__all__'


# 8. KRÓL STRZELCÓW
class TopScorerSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = TopScorer
        fields = '__all__'


# 9. OCENY MECZU
class MatchRatingSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = MatchRating
        fields = '__all__'
        # Ważne: User nie powinien sam wpisywać swojego ID.
        # Backend sam to ustawi na podstawie tokena.
        read_only_fields = ['user']


from rest_framework import serializers
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

User = get_user_model()


# --- REJESTRACJA (Bez zmian) ---
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'confirm_password')

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Hasła nie są identyczne."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        # Przypisanie do grupy User
        try:
            user_group = Group.objects.get(name='User')
            user.groups.add(user_group)
        except Group.DoesNotExist:
            pass
        return user


# --- CUSTOMOWE LOGOWANIE (JWT) ---
# Nadpisujemy domyślny serializer SimpleJWT, żeby zwrócił też is_admin i ID
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Opcjonalnie: Możesz dodać dane do wnętrza zaszyfrowanego tokena
        token['username'] = user.username
        token['is_admin'] = user.groups.filter(name='Admin').exists()

        return token

    def validate(self, attrs):
        # To generuje access i refresh token
        data = super().validate(attrs)

        # A tutaj dodajemy dane do odpowiedzi JSON (body response)
        data['user_id'] = self.user.id
        data['username'] = self.user.username
        data['is_admin'] = self.user.groups.filter(name='Admin').exists()

        return data


# --- WYLOGOWANIE (JWT) ---
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            # Wrzucamy token na czarną listę
            RefreshToken(self.token).blacklist()
        except TokenError:
            # Token już był nieważny lub błędny
            pass


# --- ZMIANA HASŁA (Bez zmian) ---
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Stare hasło jest nieprawidłowe.")
        return value