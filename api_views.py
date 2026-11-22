import django_filters
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, BasePermission

from core.permissions import IsOwner, IsOwnerOrAdmin
from restaurants.utils import owner_restaurant

from .models import FoodItem
from .serializers import FoodItemSerializer


class IsFoodOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.role == "admin" or obj.restaurant.owner_id == request.user.id


class FoodFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = FoodItem
        fields = ["restaurant", "category", "is_veg", "is_available"]


class FoodItemViewSet(viewsets.ModelViewSet):
    serializer_class = FoodItemSerializer
    filterset_class = FoodFilter
    search_fields = ["name", "description", "restaurant__name", "category__name"]
    ordering_fields = ["price", "name", "created_at"]

    def get_queryset(self):
        qs = FoodItem.objects.select_related("restaurant", "category", "inventory").order_by("name")
        user = self.request.user
        if user.is_authenticated and user.role == "admin":
            return qs
        condition = Q(is_available=True, restaurant__status="approved")
        if user.is_authenticated and user.role == "owner":
            condition |= Q(restaurant__owner=user)
        return qs.filter(condition)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action == "create":
            return [IsOwner()]
        return [IsOwnerOrAdmin(), IsFoodOwnerOrAdmin()]

    def perform_create(self, serializer):
        restaurant = owner_restaurant(self.request.user)
        if restaurant is None:
            raise ValidationError({"detail": "Create your restaurant first."})
        serializer.save(restaurant=restaurant)
