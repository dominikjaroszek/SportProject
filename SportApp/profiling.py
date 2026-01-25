# SportApp/profiling.py
from .models import UserAnalytics, MatchRating


def initialize_user_analytics(user, hype, tactical, aggression, defense, psych_type, football_profile):
    # ... (bez zmian) ...
    UserAnalytics.objects.create(
        user=user,
        base_psychology_type=psych_type,
        base_football_profile=football_profile,
        current_football_profile=football_profile,
        base_hype=float(hype),
        base_tactical=float(tactical),
        base_aggression=float(aggression),
        base_defense=float(defense),
        preference_hype=float(hype),
        preference_tactical=float(tactical),
        preference_aggression=float(aggression),
        preference_defense=float(defense)
    )


def recalculate_user_preferences(user):
    print(f"[PROFILING] Recalculate start dla: {user.username}")
    try:
        analytics = user.analytics
    except UserAnalytics.DoesNotExist:
        initialize_user_analytics(user, 50, 50, 50, 50, "Nieznany", "Nieznany")
        analytics = user.analytics

    curr_hype = analytics.base_hype
    curr_tactical = analytics.base_tactical
    curr_aggression = analytics.base_aggression
    curr_defense = analytics.base_defense

    LIMIT = 50
    # Tutaj używamy related_name 'analytics' z modelu MatchAnalytics, więc w select_related też
    recent_ratings = MatchRating.objects.filter(user=user) \
                         .select_related('match__analytics') \
                         .order_by('-created_at')[:LIMIT]

    for rating_obj in reversed(recent_ratings):
        # --- POPRAWKA TUTAJ ---
        # Było: .matchanalytics, Jest: .analytics (zgodnie z related_name)
        if not hasattr(rating_obj.match, 'analytics'):
            continue

        match_stats = rating_obj.match.analytics  # <--- POPRAWKA
        r = rating_obj.rating

        if r == 5:
            ALPHA, inverted = 0.15, False
        elif r == 4:
            ALPHA, inverted = 0.08, False
        elif r == 3:
            ALPHA, inverted = 0.02, False
        elif r == 2:
            ALPHA, inverted = 0.08, True
        elif r == 1:
            ALPHA, inverted = 0.15, True
        else:
            continue

        m_hype = match_stats.hype_score
        m_tactical = match_stats.tactical_score
        m_aggression = match_stats.aggression_score
        m_defense = match_stats.defense_score

        if inverted:
            m_hype = 100 - m_hype
            m_tactical = 100 - m_tactical
            m_aggression = 100 - m_aggression
            m_defense = 100 - m_defense

        curr_hype = (curr_hype * (1 - ALPHA)) + (m_hype * ALPHA)
        curr_tactical = (curr_tactical * (1 - ALPHA)) + (m_tactical * ALPHA)
        curr_aggression = (curr_aggression * (1 - ALPHA)) + (m_aggression * ALPHA)
        curr_defense = (curr_defense * (1 - ALPHA)) + (m_defense * ALPHA)

    analytics.preference_hype = round(curr_hype, 2)
    analytics.preference_tactical = round(curr_tactical, 2)
    analytics.preference_aggression = round(curr_aggression, 2)
    analytics.preference_defense = round(curr_defense, 2)

    if hasattr(analytics, 'update_current_football_profile'):
        analytics.update_current_football_profile()

    analytics.save()


def update_single_rating(user, rating_obj):
    print(f"[PROFILING] Single Update start dla: {user.username}, Mecz: {rating_obj.match}")
    try:
        analytics = user.analytics
    except UserAnalytics.DoesNotExist:
        initialize_user_analytics(user, 50, 50, 50, 50, "Nieznany", "Nieznany")
        analytics = user.analytics

    # --- POPRAWKA TUTAJ ---
    # Używamy .analytics zamiast .matchanalytics
    if not hasattr(rating_obj.match, 'analytics'):
        print(f"[PROFILING] BŁĄD: Mecz {rating_obj.match} nie ma atrybutu .analytics")
        return

    match_stats = rating_obj.match.analytics  # <--- POPRAWKA
    print(f"[PROFILING] Statystyki meczu pobrane. Hype: {match_stats.hype_score}")

    r = rating_obj.rating

    if r == 5:
        ALPHA, inverted = 0.15, False
    elif r == 4:
        ALPHA, inverted = 0.08, False
    elif r == 3:
        ALPHA, inverted = 0.02, False
    elif r == 2:
        ALPHA, inverted = 0.08, True
    elif r == 1:
        ALPHA, inverted = 0.15, True
    else:
        return

    m_hype = match_stats.hype_score
    m_tactical = match_stats.tactical_score
    m_aggression = match_stats.aggression_score
    m_defense = match_stats.defense_score

    if inverted:
        m_hype = 100 - m_hype
        m_tactical = 100 - m_tactical
        m_aggression = 100 - m_aggression
        m_defense = 100 - m_defense

    # Obliczenia...
    analytics.preference_hype = (analytics.preference_hype * (1 - ALPHA)) + (m_hype * ALPHA)
    analytics.preference_tactical = (analytics.preference_tactical * (1 - ALPHA)) + (m_tactical * ALPHA)
    analytics.preference_aggression = (analytics.preference_aggression * (1 - ALPHA)) + (m_aggression * ALPHA)
    analytics.preference_defense = (analytics.preference_defense * (1 - ALPHA)) + (m_defense * ALPHA)

    analytics.preference_hype = round(analytics.preference_hype, 2)
    analytics.preference_tactical = round(analytics.preference_tactical, 2)
    analytics.preference_aggression = round(analytics.preference_aggression, 2)
    analytics.preference_defense = round(analytics.preference_defense, 2)

    print(f"[PROFILING] Nowe preferencje Hype: {analytics.preference_hype}")

    if hasattr(analytics, 'update_current_football_profile'):
        analytics.update_current_football_profile()

    analytics.save()