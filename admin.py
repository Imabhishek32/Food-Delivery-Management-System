from django.contrib import admin

from .models import FoodCategory, FoodItem


@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name",)


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ("name", "restaurant", "category", "price", "discount_percent", "is_available", "is_veg")
    list_filter = ("is_available", "is_veg", "category", "restaurant")
    search_fields = ("name", "restaurant__name")
