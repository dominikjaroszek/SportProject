from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView  # Ważne dla JWT

# Importujemy Twoje widoki (ViewSets i Auth Views)
from .views import (
    # ViewSety (Dane)
    UserViewSet, LeagueViewSet, SeasonViewSet, TeamViewSet,
    MatchViewSet, StandingViewSet, TopScorerViewSet, MatchRatingViewSet,

    # Auth Views (Logowanie/Rejestracja)
    RegisterView, MyTokenObtainPairView, LogoutView,
    ChangePasswordView, CurrentUserView
)

# 1. KONFIGURACJA ROUTERA (To obsługuje /api/matches, /api/teams itp.)
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'leagues', LeagueViewSet)
router.register(r'seasons', SeasonViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'matches', MatchViewSet)
router.register(r'standings', StandingViewSet)
router.register(r'top-scorers', TopScorerViewSet)
router.register(r'ratings', MatchRatingViewSet)

# 2. LISTA URLI (Łączymy Router + Endpointy Auth)
urlpatterns = [

    path('', include(router.urls)),

    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', MyTokenObtainPairView.as_view(), name='auth_login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Standardowy widok JWT
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth_change_password'),
    path('auth/me/', CurrentUserView.as_view(), name='auth_me'),
]