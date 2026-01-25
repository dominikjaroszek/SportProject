# SportApp/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import MatchRating
from .profiling import recalculate_user_preferences, update_single_rating

# UWAGA: Usunęliśmy sygnał post_save dla Usera, bo inicjalizację robimy w RegisterView.

@receiver(post_save, sender=MatchRating)
def update_analytics_on_rating_save(sender, instance, created, **kwargs):
    print("--- Uruchamiam1 update_single_rating ---")  # <--- DEBUG
    if created:
        print("--- Uruchamiam2 update_single_rating ---") # <--- DEBUG
        update_single_rating(instance.user, instance)
    else:
        print("--- Uruchamiam3 update_single_rating ---") # <--- DEBUG
        recalculate_user_preferences(instance.user)

@receiver(post_delete, sender=MatchRating)
def update_analytics_on_rating_delete(sender, instance, **kwargs):
    # 3. DELETE -> Pełne przeliczenie (bezpieczne)
    recalculate_user_preferences(instance.user)