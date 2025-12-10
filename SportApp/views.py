from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import User, League, Season, Team, Match, Standing, TopScorer, MatchRating
from .serializers import (
    UserSerializer, LeagueSerializer, SeasonSerializer, TeamSerializer,
    MatchSerializer, StandingSerializer, TopScorerSerializer, MatchRatingSerializer
)
# 1. IMPORTUJEMY TWOJE CUSTOMOWE UPRAWNIENIA
from .permissions import IsUserGroup, IsAdminGroup


# --- 1. USER VIEW ---
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # Tylko Admin może zarządzać użytkownikami
    permission_classes = [IsAdminGroup]


# --- 2. KATALOGI (Ligi, Sezony, Drużyny) ---
# Tutaj stosujemy logikę: USER czyta (GET), ADMIN zmienia (POST/PUT/DELETE)

class LeagueViewSet(viewsets.ModelViewSet):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsUserGroup()]  # User i Admin mogą oglądać
        return [IsAdminGroup()]  # Tylko Admin może dodawać/edytować


class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.all().order_by('-year')
    serializer_class = SeasonSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['league', 'is_current']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsUserGroup()]
        return [IsAdminGroup()]


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all().order_by('name')
    serializer_class = TeamSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['league']
    search_fields = ['name', 'city']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsUserGroup()]
        return [IsAdminGroup()]


# --- 3. CORE (Mecze) ---
class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all().order_by('-date')
    serializer_class = MatchSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['season', 'home_team', 'away_team', 'date']

    def get_permissions(self):
        # 1. Lista meczów i szczegóły -> Dla Userów (i Adminów)
        if self.action in ['list', 'retrieve']:
            return [IsUserGroup()]
        # 2. Dodawanie, edycja, usuwanie meczów -> Tylko Admin
        return [IsAdminGroup()]


# --- 4. TABELE I STRZELCY ---
class StandingViewSet(viewsets.ModelViewSet):
    queryset = Standing.objects.all().order_by('position')
    serializer_class = StandingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['season']

    # Tabela ligowa to dane tylko do odczytu dla Usera
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsUserGroup()]
        return [IsAdminGroup()]


# --- 5. OCENY (Wyjątek!) ---
# Tutaj User MUSI mieć prawo zapisu (POST), żeby dodać ocenę.

class MatchRatingViewSet(viewsets.ModelViewSet):
    queryset = MatchRating.objects.all().order_by('-created_at')
    serializer_class = MatchRatingSerializer

    def get_permissions(self):
        # Akcja create (dodanie oceny) -> Dostępna dla Usera
        if self.action == 'create':
            return [IsUserGroup()]

        # Oglądanie ocen -> Dostępne dla Usera
        if self.action in ['list', 'retrieve']:
            return [IsUserGroup()]

        # Edycja/Usuwanie -> Tutaj decydujesz.
        # Zazwyczaj Admin może usuwać wszystko, a User tylko swoje (to wymagałoby IsOwner).
        # Dla uproszczenia tutaj: Tylko Admin może usuwać/edytować "na twardo".
        return [IsAdminGroup()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TopScorerViewSet(viewsets.ModelViewSet):
    # Sortujemy od największej liczby goli
    queryset = TopScorer.objects.all().order_by('-goals')
    serializer_class = TopScorerSerializer

    # Filtrowanie jest kluczowe - chcemy zobaczyć strzelców dla konkretnego sezonu
    # np. /api/top-scorers/?season=1
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['season']

    def get_permissions(self):
        # 1. Przeglądanie listy strzelców -> Dla Userów (i Adminów)
        if self.action in ['list', 'retrieve']:
            return [IsUserGroup()]

        # 2. Edycja, dodawanie, usuwanie -> Tylko Admin
        # (Dane te zazwyczaj wpadają automatycznie ze skryptu, więc user nie może ich tykać)
        return [IsAdminGroup()]

from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    RegisterSerializer, MyTokenObtainPairSerializer,
    LogoutSerializer, ChangePasswordSerializer, UserSerializer
)

# 1. REJESTRACJA
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

# 2. LOGOWANIE (JWT)
# Dziedziczymy po widoku z biblioteki, ale podmieniamy serializer na nasz
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

# 3. WYLOGOWANIE (JWT - Blacklist)
class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Pomyślnie wylogowano (token unieważniony)."}, status=status.HTTP_204_NO_CONTENT)

# 4. ZMIANA HASŁA
class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"message": "Hasło zostało zmienione."}, status=status.HTTP_200_OK)

# 5. INFO O KONCIE (ME)
class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user