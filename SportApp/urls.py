from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserViewSet,
    LeagueViewSet,
    SeasonViewSet,
    TeamViewSet,
    MatchViewSet,
    StandingViewSet,
    TopScorerViewSet,
    MatchRatingViewSet,

    RegisterView,
    MyTokenObtainPairView,
    LogoutView,
    ChangePasswordView,
    CurrentUserView,

    GlobalSearchView, AdminCommandView, UserAnalyticsRadarView, RecommendedMatchesView
)
from .views import TopMatchesForUserStyleView
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'leagues', LeagueViewSet)
router.register(r'seasons', SeasonViewSet)
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'matches', MatchViewSet, basename='match')
router.register(r'standings', StandingViewSet)
router.register(r'top_scorers', TopScorerViewSet)
router.register(r'ratings', MatchRatingViewSet, basename='rating')

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
    path('search/', GlobalSearchView.as_view(), name='global_search'),
    path('finished-matches/<str:league_name>/<str:season_name>/<int:limit>/',
         MatchViewSet.as_view({'get': 'list_finished'}), name='finished-list'),
    path('finished-matches/round/',
         MatchViewSet.as_view({'get': 'list_finished_round'}), name='finished-round'),
    path('upcoming-matches/<str:league_name>/<str:season_name>/<int:limit>/',
         MatchViewSet.as_view({'get': 'list_upcoming'}), name='upcoming-list'),
    path('upcoming-matches/round/',
         MatchViewSet.as_view({'get': 'list_upcoming_round'}), name='upcoming-round'),
    path('upcoming-matches/scores/',
         MatchViewSet.as_view({'get': 'list_upcoming_scores'}), name='upcoming-scores'),
    path('', include(router.urls)),
]