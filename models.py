from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from core.models import TimeStampedModel
from core.validators import validate_image_size


class FoodCategory(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap Icons class, e.g. bi-cup-hot")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "food categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class FoodItem(TimeStampedModel):
    restaurant = models.ForeignKey("restaurants.Restaurant", on_delete=models.CASCADE, related_name="food_items")
    category = models.ForeignKey(FoodCategory, on_delete=models.PROTECT, related_name="food_items")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    discount_percent = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(90)])
    image = models.ImageField(upload_to="food/", blank=True, null=True, validators=[validate_image_size])
    is_veg = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "name"], name="unique_food_name_per_restaurant"),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_available"]),
            models.Index(fields=["category", "price"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    @property
    def final_price(self):
        """Price after the item-level discount. This is the server-side source of truth."""
        discount = self.price * self.discount_percent / Decimal("100")
        return (self.price - discount).quantize(Decimal("0.01"))

    @property
    def stock(self):
        inventory = getattr(self, "inventory", None)
        return inventory.quantity if inventory else 0

    @property
    def in_stock(self):
        return self.stock > 0
