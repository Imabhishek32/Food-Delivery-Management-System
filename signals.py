from django.db.models.signals import post_save
from django.dispatch import receiver

from inventory.models import Inventory

from .models import FoodItem


@receiver(post_save, sender=FoodItem)
def create_inventory(sender, instance, created, **kwargs):
    """Every food item always has exactly one Inventory row (starts at 0 = out of stock)."""
    if created:
        Inventory.objects.get_or_create(food_item=instance)
