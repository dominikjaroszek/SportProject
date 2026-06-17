from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import MatchRating
from .profiling import recalculate_user_preferences, update_single_rating

@receiver(post_save, sender=MatchRating)
def update_analytics_on_rating_save(sender, instance, created, **kwargs):
    if created:
        update_single_rating(instance.user, instance)
    else:
        recalculate_user_preferences(instance.user)

@receiver(post_delete, sender=MatchRating)
def update_analytics_on_rating_delete(sender, instance, **kwargs):
    recalculate_user_preferences(instance.user)