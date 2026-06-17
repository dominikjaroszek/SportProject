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
    season = django_filters.CharFilter(method='filter_by_season')

    class Meta:
        model = Standing
        fields = ['league', 'season']

    def filter_by_season(self, queryset, name, value):

        if not value:
            return queryset

        year_val = value
        if '/' in value:
            year_val = value.split('/')[0]
        elif '-' in value:
            year_val = value.split('-')[0]

        return queryset.filter(season__year=year_val.strip())