import math
from django.utils import timezone
from io import StringIO

from django.core.management import call_command
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.response import Response
from rest_framework import viewsets, permissions, filters, generics, status, views
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from django.db import IntegrityError
from rest_framework.exceptions import ValidationError

from .filters import TopScorerFilter, StandingFilter
from .models import User, League, Season, Team, Match, Standing, TopScorer, MatchRating, UserAnalytics
from .profiling import initialize_user_analytics
from .serializers import (
    UserSerializer, LeagueSerializer, SeasonSerializer, StandingSerializer, TopScorerSerializer,
    RegisterSerializer, MyTokenObtainPairSerializer,
    LogoutSerializer, ChangePasswordSerializer, HomeStandingSerializer, AwayStandingSerializer, TeamMatchSerializer,
    TeamDetailSerializer, SearchResultSerializer, MatchScoreSerializer, MatchListSerializer, MatchDetailSerializer,
    MatchRatingSerializer, MatchBaseSerializer, SeasonDetailSerializer, UserRadarChartSerializer,
    PersonalizedMatchSerializer
)
from .permissions import IsUserGroup, IsAdminGroup, IsOwnerOrAdmin
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action
from django.db.models import F, Q, Avg


class AdminCommandView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, command_name):
        out = StringIO()

        try:
            if command_name == 'calculate_analytics':
                call_command('calculate_analytics', stdout=out)

            elif command_name == 'calculate_benchmarks':
                call_command('calculate_benchmarks', stdout=out)

            elif command_name == 'calculate_history_analytics':
                call_command('calculate_history_analytics', stdout=out)

            elif command_name == 'fetch_match_statistics':
                call_command('fetch_match_statistics', stdout=out)

            elif command_name == 'sync_full_season':
                options = request.data
                args = []
                if options.get('all'):
                    args.append('--all')
                else:
                    if options.get('setup'):
                        args.append('--setup')
                    if options.get('matches'):
                        args.append('--matches')
                    if options.get('standings'):
                        args.append('--standings')

                call_command('sync_full_season', *args, stdout=out)

            else:
                return Response({"error": "Unknown command"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "status": "success",
                "message": "Command executed successfully.",
                "output": out.getvalue()
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminGroup]


class LeagueViewSet(viewsets.ModelViewSet):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer
    lookup_field = 'name'
    lookup_value_regex = '[^/]+'

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'names', 'seasons', 'season_details']:
            return [AllowAny()]
        return [IsAdminGroup()]

    @extend_schema(
        description="Zwraca listę obiektów lig (nazwa i logo).",
        responses={200: {"type": "array", "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "logo": {"type": "string"}
            }
        }}}
    )
    @action(detail=False, methods=['get'])
    def names(self, request):
        leagues = League.objects.values('name', 'logo').order_by('name')
        return Response(list(leagues))

    @extend_schema(
        description="Zwraca wszystkie sezony dla danej ligi.",
        responses=SeasonSerializer(many=True)
    )
    @action(detail=True, methods=['get'])
    def seasons(self, request, name=None):
        league = self.get_object()
        seasons = league.season_set.all().order_by('-year')
        serializer = SeasonSerializer(seasons, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Zwraca szczegóły konkretnego sezonu dla danej ligi.",
        responses=SeasonDetailSerializer
    )
    @action(detail=True, methods=['get'], url_path=r'(?P<year>[\d-]+)')
    def season_details(self, request, name=None, year=None):
        league = self.get_object()

        if '-' in str(year):
            year_val = str(year).split('-')[0]
        else:
            year_val = year

        season = get_object_or_404(Season, league=league, year=year_val)
        serializer = SeasonDetailSerializer(season)
        return Response(serializer.data)


class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.all().order_by('-year')
    serializer_class = SeasonSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['league', 'is_current']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'current_year']:
            return [AllowAny()]
        return [IsAdminGroup()]

    @extend_schema(
        description="Zwraca tylko rok aktualnego sezonu jako liczbę (np. 2025).",
        responses={200: int}
    )
    @action(detail=False, methods=['get'], url_path='current-year')
    def current_year(self, request):
        current_season = Season.objects.filter(is_current=True).order_by('-year').first()

        if not current_season:
            current_season = Season.objects.order_by('-year').first()

        if current_season:
            return Response(current_season.year)

        return Response(None, status=404)


class GlobalSearchView(views.APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter(name='value', description='Szukana fraza', required=True, type=str)],
        responses={200: SearchResultSerializer(many=True)},
        description="Wyszukuje drużyny i ligi po nazwie."
    )
    def get(self, request):
        query = request.query_params.get('value', '')

        if len(query) < 2:
            return Response({"error": "Wpisz co najmniej 2 znaki"}, status=status.HTTP_400_BAD_REQUEST)

        results = []

        teams = Team.objects.filter(name__icontains=query)[:5]
        for team in teams:
            results.append({
                "name": team.name,
                "type": "team",
                "logo": team.logo,
                "id": team.id,
            })

        leagues = League.objects.filter(name__icontains=query)[:5]
        for league in leagues:
            results.append({
                "name": league.name,
                "type": "league",
                "logo": league.logo,
                "id": league.id,
            })

        return Response(results)


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamDetailSerializer
    lookup_field = 'name'
    lookup_value_regex = '[^/]+'

    @extend_schema(responses=TeamMatchSerializer(many=True))
    @action(detail=True, methods=['get'], url_path=r'finished/(?P<limit>\d+)')
    def finished(self, request, name=None, limit=None):
        team = self.get_object()

        matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            status='Finished'
        ).select_related('home_team', 'away_team').order_by('-date')

        if limit:
            matches = matches[:int(limit)]

        serializer = TeamMatchSerializer(matches, many=True)
        return Response(serializer.data)

    @extend_schema(responses=TeamMatchSerializer(many=True))
    @action(detail=True, methods=['get'], url_path=r'upcoming/(?P<limit>\d+)')
    def upcoming(self, request, name=None, limit=None):
        team = self.get_object()

        matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            status='Scheduled'
        ).select_related('home_team', 'away_team').order_by('date')

        if limit:
            matches = matches[:int(limit)]

        serializer = TeamMatchSerializer(matches, many=True)
        return Response(serializer.data)


class MatchRatingViewSet(viewsets.ModelViewSet):
    queryset = MatchRating.objects.all().order_by('-created_at')
    serializer_class = MatchRatingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['match__api_id', 'user']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]

        return [IsUserGroup()]

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError:
            raise ValidationError({
                "detail": "Oceniłeś już ten mecz. Użyj edycji, aby zmienić ocenę."
            })

    @extend_schema(
        parameters=[OpenApiParameter(name='match_id', description='ID Meczu (api_id)', required=True, type=int)],
        responses={200: MatchRatingSerializer, 204: None},
        description="Zarządzaj swoją oceną podając tylko ID meczu."
    )
    @action(detail=False, methods=['get', 'patch', 'delete'], url_path='my-rating')
    def my_rating(self, request):
        match_id = request.query_params.get('match_id')
        if not match_id:
            return Response({"error": "Brak parametru ?match_id="}, status=status.HTTP_400_BAD_REQUEST)

        rating = get_object_or_404(MatchRating, user=request.user, match__api_id=match_id)

        if request.method == 'GET':
            return Response(self.get_serializer(rating).data)

        elif request.method == 'PATCH':
            serializer = self.get_serializer(rating, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        elif request.method == 'DELETE':
            rating.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.select_related(
        'home_team', 'away_team', 'season', 'season__league'
    ).annotate(
        avg_rating=Avg('ratings__rating')
    ).order_by('-date')

    serializer_class = MatchDetailSerializer

    lookup_field = 'api_id'

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'season': ['exact'],
        'home_team': ['exact'],
        'away_team': ['exact'],
        'date': ['exact', 'gte', 'lte'],
        'season__league': ['exact'],
    }
    ordering_fields = ['date', 'avg_rating']
    ordering = ['-date']

    def get_permissions(self):
        user_actions = [
            'list', 'retrieve', 'get_average',
            'list_finished', 'list_finished_round',
            'list_upcoming', 'list_upcoming_round',
            'list_upcoming_scores'
        ]

        if self.action in user_actions:
            return [AllowAny()]

        return [IsAdminGroup()]

    @extend_schema(
        description="Pobiera zakończone mecze ze wszystkich lig dla ich aktualnych sezonów, pogrupowane ligami. Idealne dla Home Page.",
        responses={200: MatchListSerializer(many=True)}
    )
    def list_finished_round(self, request):
        matches = self.queryset.filter(
            status='Finished',
            season__is_current=True
        ).order_by('-date')

        grouped_data = {}
        for match in matches:
            league_name = match.season.league.name
            if league_name not in grouped_data:
                grouped_data[league_name] = []
            grouped_data[league_name].append(match)

        result = []
        for league_name, match_list in grouped_data.items():
            result.append({
                "league_name": league_name,
                "matches": MatchListSerializer(match_list, many=True).data
            })

        return Response(result)

    @extend_schema(
        description="Pobiera nadchodzące mecze ze wszystkich lig dla ich aktualnych sezonów, pogrupowane ligami. Idealne dla Home Page.",
        responses={200: MatchListSerializer(many=True)}
    )
    def list_upcoming_round(self, request):
        matches = self.queryset.filter(
            status='Scheduled',
            season__is_current=True
        ).order_by('date')

        grouped_data = {}
        for match in matches:
            league_name = match.season.league.name
            if league_name not in grouped_data:
                grouped_data[league_name] = []
            grouped_data[league_name].append(match)

        result = []
        for league_name, match_list in grouped_data.items():
            result.append({
                "league_name": league_name,
                "matches": MatchListSerializer(match_list, many=True).data
            })

        return Response(result)

    def list_finished(self, request, league_name, season_name, limit):
        matches = self.queryset.filter(
            status='Finished',
            season__league__name__iexact=league_name.replace('-', ' '),
            season__year=season_name
        ).order_by('-date')[:int(limit)]
        return Response(MatchListSerializer(matches, many=True).data)

    def list_upcoming(self, request, league_name, season_name, limit):
        matches = self.queryset.filter(
            status='Scheduled',
            season__league__name__iexact=league_name.replace('-', ' '),
            season__year=season_name
        ).order_by('date')[:int(limit)]
        return Response(MatchBaseSerializer(matches, many=True).data)

    def list_upcoming_scores(self, request):
        matches = self.queryset.filter(
            status='Scheduled',
            season__is_current=True
        ).select_related('analytics').order_by('date')

        grouped_data = {}
        for match in matches:
            league_name = match.season.league.name

            if league_name not in grouped_data:
                grouped_data[league_name] = []

            grouped_data[league_name].append(match)

        result = []
        for league_name, match_list in grouped_data.items():
            result.append({
                "league_name": league_name,
                "matches": MatchScoreSerializer(match_list, many=True).data
            })

        return Response(result)

    @extend_schema(
        description="Pobierz tylko średnią ocenę dla danego meczu",
        responses={200: {"type": "object", "properties": {"average_rating": {"type": "number"}}}}
    )
    @action(detail=True, methods=['get'], url_path='average-rating')
    def get_average(self, request, api_id=None):
        match = self.get_object()
        avg = match.avg_rating if match.avg_rating else 0.0
        return Response({"average_rating": round(avg, 2)})


class StandingViewSet(viewsets.ModelViewSet):
    queryset = Standing.objects.select_related('team', 'season', 'season__league').all()
    serializer_class = StandingSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = StandingFilter
    ordering_fields = ['position', 'points']
    ordering = ['position']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'home', 'away', 'general']:
            return [AllowAny()]
        return [IsAdminGroup()]

    def _get_annotated_queryset(self, prefix=''):
        queryset = self.filter_queryset(self.get_queryset())

        p_win = f'{prefix}win' if prefix else 'win'
        p_draw = f'{prefix}draw' if prefix else 'draw'
        p_gf = f'{prefix}goals_for' if prefix else 'goals_for'
        p_ga = f'{prefix}goals_against' if prefix else 'goals_against'

        return queryset.annotate(
            calculated_points=(F(p_win) * 3) + F(p_draw),
            calculated_diff=F(p_gf) - F(p_ga)
        ).order_by('-calculated_points', '-calculated_diff', f'-{p_gf}')

    @extend_schema(
        description="Pobiera ogólną tabelę ligową.",
        parameters=[
            OpenApiParameter(name='league', description='Nazwa ligi', required=False, type=str),
            OpenApiParameter(name='season', description='Sezon (np. 2024/2026)', required=False, type=str),
        ],
        responses=StandingSerializer(many=True)
    )
    @action(detail=False, methods=['get'])
    def general(self, request):
        queryset = self.filter_queryset(self.get_queryset()).order_by('position')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses=HomeStandingSerializer(many=True)
    )
    @action(detail=False, methods=['get'])
    def home(self, request):
        queryset = self._get_annotated_queryset(prefix='home_')

        serializer = HomeStandingSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses=AwayStandingSerializer(many=True)
    )
    @action(detail=False, methods=['get'])
    def away(self, request):
        queryset = self._get_annotated_queryset(prefix='away_')

        serializer = AwayStandingSerializer(queryset, many=True)
        return Response(serializer.data)


class TopMatchesForUserStyleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            analytics = user.analytics
        except UserAnalytics.DoesNotExist:
            return Response({"error": "Brak profilu analitycznego."}, status=404)

        user_stats = {
            'analytics__hype_score': analytics.preference_hype,
            'analytics__tactical_score': analytics.preference_tactical,
            'analytics__aggression_score': analytics.preference_aggression,
            'analytics__defense_score': analytics.preference_defense,
        }

        dominant_category = max(user_stats, key=user_stats.get)

        order_by_field = f"-{dominant_category}"

        top_matches = Match.objects.filter(
            status='Scheduled',
            analytics__isnull=False
        ).select_related('analytics').order_by(order_by_field)[:2]

        stat_name = dominant_category.split('__')[1]
        for match in top_matches:
            match.match_score = getattr(match.analytics, stat_name, 0)

        serializer = PersonalizedMatchSerializer(top_matches, many=True)
        return Response(serializer.data)


class TopScorerViewSet(viewsets.ModelViewSet):
    queryset = TopScorer.objects.select_related(
        'team', 'season', 'season__league'
    ).all().order_by('-goals')

    serializer_class = TopScorerSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = TopScorerFilter

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'canadian', 'general']:
            return [AllowAny()]
        return [IsAdminGroup()]

    @extend_schema(
        description="Pobiera listę strzelców (parametry: league, season).",
        parameters=[
            OpenApiParameter(name='league', description='Nazwa ligi', required=False, type=str),
            OpenApiParameter(name='season', description='Sezon (np. 2025/2026)', required=False, type=str),
        ],
        responses=TopScorerSerializer(many=True)
    )
    @action(detail=False, methods=['get'])
    def general(self, request):
        queryset = self.get_queryset()

        league_name = request.query_params.get('league')
        season_str = request.query_params.get('season')

        if league_name:
            queryset = queryset.filter(season__league__name__iexact=league_name)

        if season_str:
            if '/' in season_str:
                year_val = season_str.split('/')[0].strip()
            elif '-' in season_str:
                year_val = season_str.split('-')[0].strip()
            else:
                year_val = season_str.strip()

            queryset = queryset.filter(season__year=year_val)

        serializer = TopScorerSerializer(queryset, many=True)
        return Response(serializer.data)


class UserAnalyticsRadarView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        analytics = get_object_or_404(UserAnalytics, user=request.user)

        serializer = UserRadarChartSerializer(analytics)
        return Response(serializer.data)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            first_key = next(iter(serializer.errors))
            error_content = serializer.errors[first_key][0]
            return Response(
                {"message": error_content},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.save()

        base_hype = request.data.get('base_hype', 50.0)
        base_tactical = request.data.get('base_tactical', 50.0)
        base_aggression = request.data.get('base_aggression', 50.0)
        base_defense = request.data.get('base_defense', 50.0)

        psych_type = request.data.get('personality_type', 'Nieznany')
        football_profile = request.data.get('football_profile', 'Nieznany')

        initialize_user_analytics(
            user=user,
            hype=base_hype,
            tactical=base_tactical,
            aggression=base_aggression,
            defense=base_defense,
            psych_type=psych_type,
            football_profile=football_profile
        )

        return Response(
            {"message": "Rejestracja udana! Możesz się teraz zalogować."},
            status=status.HTTP_201_CREATED
        )


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Pomyślnie wylogowano (token unieważniony)."}, status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch', 'put']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})

        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({"message": "Hasło zostało pomyślnie zmienione."}, status=status.HTTP_200_OK)


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class RecommendedMatchesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            user_analytics = user.analytics
        except UserAnalytics.DoesNotExist:
            return Response(
                {"error": "User analytics profile not found. Please rate some matches first."},
                status=status.HTTP_404_NOT_FOUND
            )

        now = timezone.now()
        upcoming_matches = Match.objects.filter(
            status='Scheduled',
            date__gte=now,
            analytics__isnull=False
        ).select_related('analytics', 'home_team', 'away_team')

        scored_matches = []

        u_hype = user_analytics.preference_hype
        u_tactical = user_analytics.preference_tactical
        u_aggression = user_analytics.preference_aggression
        u_defense = user_analytics.preference_defense

        for match in upcoming_matches:
            m_analytics = match.analytics

            diff_hype = (u_hype - m_analytics.hype_score) ** 2
            diff_tactical = (u_tactical - m_analytics.tactical_score) ** 2
            diff_aggression = (u_aggression - m_analytics.aggression_score) ** 2
            diff_defense = (u_defense - m_analytics.defense_score) ** 2

            euclidean_distance = math.sqrt(diff_hype + diff_tactical + diff_aggression + diff_defense)

            match_fit_percentage = max(0, 100 - (euclidean_distance / 2))

            match.match_score = round(match_fit_percentage, 1)

            scored_matches.append((euclidean_distance, match))

        scored_matches.sort(key=lambda x: x[0])

        top_matches = [item[1] for item in scored_matches[:2]]

        serializer = PersonalizedMatchSerializer(top_matches, many=True)
        return Response(serializer.data)