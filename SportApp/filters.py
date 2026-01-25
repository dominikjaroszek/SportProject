import django_filters
from .models import TopScorer, Standing


class TopScorerFilter(django_filters.FilterSet):
    league = django_filters.CharFilter(field_name='season__league__name', lookup_expr='iexact')

    season = django_filters.CharFilter(field_name='season__year', lookup_expr='exact')

    class Meta:
        model = TopScorer
        fields = ['league', 'season']


class StandingFilter(django_filters.FilterSet):
    league = django_filters.CharFilter(field_name='season__league__name', lookup_expr='iexact')

    season = django_filters.CharFilter(field_name='season__year', lookup_expr='exact')

    class Meta:
        model = Standing
        fields = ['league', 'season']