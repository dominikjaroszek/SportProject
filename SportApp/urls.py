from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Importujemy wszystkie widoki z Twojego pliku views.py (lub pakietu views/)
from .views import (
    # ViewSety (Dane)
    UserViewSet,
    LeagueViewSet,
    SeasonViewSet,
    TeamViewSet,
    MatchViewSet,
    StandingViewSet,
    TopScorerViewSet,
    MatchRatingViewSet,

    # Auth Views (Logowanie/Rejestracja)
    RegisterView,
    MyTokenObtainPairView,
    LogoutView,
    ChangePasswordView,
    CurrentUserView,

    # Narzędzia
    GlobalSearchView, AdminCommandView, UserAnalyticsRadarView, RecommendedMatchesView
)
from .views import TopMatchesForUserStyleView
# --- 1. KONFIGURACJA ROUTERA (Automatyczne endpointy CRUD) ---
# Router tworzy ścieżki typu: /api/matches/, /api/matches/{id}/, /api/leagues/ itp.
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'leagues', LeagueViewSet)
router.register(r'seasons', SeasonViewSet)
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'matches', MatchViewSet, basename='match')
router.register(r'standings', StandingViewSet)
router.register(r'top_scorers', TopScorerViewSet)
router.register(r'ratings', MatchRatingViewSet, basename='rating')



# --- 2. LISTA URLI (Customowe + Auth + Router) ---
urlpatterns = [
path('matches/recommended-by-style/', TopMatchesForUserStyleView.as_view(), name='recommended-by-style'),
    path('matches/recommended/', RecommendedMatchesView.as_view(), name='recommended-matches'),
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', MyTokenObtainPairView.as_view(), name='auth_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth_change_password'),
    path('auth/me/', CurrentUserView.as_view(), name='auth_me'),

    path('admin/run-command/<str:command_name>/', AdminCommandView.as_view(), name='admin-run-command'),

    path('analytics/radar/', UserAnalyticsRadarView.as_view(), name='user-radar-chart'),
    # --- B. GLOBAL SEARCH ---
    path('search/', GlobalSearchView.as_view(), name='global_search'),

    # --- C. CUSTOM MATCH ENDPOINTS (Ręczne mapowanie metod z MatchViewSet) ---

    # 1. Finished Matches (z parametrami w URL)
    # np. /api/finished-matches/Premier League/2023-2024/10/
    path('finished-matches/<str:league_name>/<str:season_name>/<int:limit>/',
         MatchViewSet.as_view({'get': 'list_finished'}), name='finished-list'),

    # 2. Finished Round (parametry w query string ?league=...&round=...)
    path('finished-matches/round/',
         MatchViewSet.as_view({'get': 'list_finished_round'}), name='finished-round'),

    # 3. Upcoming Matches (z parametrami w URL)
    path('upcoming-matches/<str:league_name>/<str:season_name>/<int:limit>/',
         MatchViewSet.as_view({'get': 'list_upcoming'}), name='upcoming-list'),

    # 4. Upcoming Round (parametry w query string)
    path('upcoming-matches/round/',
         MatchViewSet.as_view({'get': 'list_upcoming_round'}), name='upcoming-round'),

    # 5. Upcoming Scores (Wskaźniki/Analytics)
    path('upcoming-matches/scores/',
         MatchViewSet.as_view({'get': 'list_upcoming_scores'}), name='upcoming-scores'),

    # --- D. ROUTER (Musi być na końcu lub dołączony przez include) ---
    # To obsługuje wszystkie standardowe ścieżki zdefiniowane w sekcji 1
    path('', include(router.urls)),
]