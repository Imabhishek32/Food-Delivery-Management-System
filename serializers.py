from rest_framework import serializers

from inventory.models import Inventory
from restaurants.utils import owner_restaurant

from .models import FoodCategory, FoodItem


class FoodCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = ("id", "name", "slug", "icon")


class FoodItemSerializer(serializers.ModelSerializer):
    restaurant_id = serializers.IntegerField(read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    final_price = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    stock = serializers.SerializerMethodField()
    stock_quantity = serializers.IntegerField(write_only=True, required=False, min_value=0)

    class Meta:
        model = FoodItem
        fields = ("id", "restaurant_id", "restaurant_name", "category", "category_name", "name", "description",
                  "price", "discount_percent", "final_price", "image", "is_veg", "is_available",
                  "stock", "stock_quantity", "created_at")
        read_only_fields = ("id", "created_at")

    def get_stock(self, obj):
        return obj.stock

    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError("This category is not active.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        restaurant = self.instance.restaurant if self.instance else owner_restaurant(request.user)
        name = attrs.get("name", self.instance.name if self.instance else None)
        if restaurant and name:
            duplicates = FoodItem.objects.filter(restaurant=restaurant, name__iexact=name)
            if self.instance:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError({"name": "This restaurant already has a food item with that name."})
        return attrs

    def _apply_stock(self, instance, stock):
        if stock is not None:
            inventory, _ = Inventory.objects.get_or_create(food_item=instance)
            inventory.quantity = stock
            inventory.save()

    def create(self, validated_data):
        stock = validated_data.pop("stock_quantity", None)
        instance = super().create(validated_data)
        self._apply_stock(instance, stock)
        return instance

    def update(self, instance, validated_data):
        stock = validated_data.pop("stock_quantity", None)
        instance = super().update(instance, validated_data)
        self._apply_stock(instance, stock)
        return instance
