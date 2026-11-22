from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.decorators import role_required
from core.utils import paginate, parse_decimal
from restaurants.models import Restaurant
from restaurants.utils import owner_restaurant

from .forms import FoodItemForm
from .models import FoodCategory, FoodItem


def food_list(request):
    """Public menu / search page: search by name, filter by category, price and veg."""
    qs = FoodItem.objects.filter(is_available=True, restaurant__status=Restaurant.Status.APPROVED) \
        .select_related("restaurant", "category", "inventory")
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    min_price = parse_decimal(request.GET.get("min_price"))
    max_price = parse_decimal(request.GET.get("max_price"))
    veg = request.GET.get("veg") == "1"
    sort = request.GET.get("sort", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(restaurant__name__icontains=q))
    if category:
        qs = qs.filter(category__slug=category)
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    if veg:
        qs = qs.filter(is_veg=True)
    qs = qs.order_by({"price_asc": "price", "price_desc": "-price"}.get(sort, "name"))
    page = paginate(request, qs, 12)
    return render(request, "public/foods.html", {
        "page_obj": page, "categories": FoodCategory.objects.filter(is_active=True),
        "q": q, "active_category": category, "min_price": request.GET.get("min_price", ""),
        "max_price": request.GET.get("max_price", ""), "veg": veg, "sort": sort,
    })


def food_detail(request, pk):
    food = get_object_or_404(FoodItem.objects.select_related("restaurant", "category", "inventory"), pk=pk)
    previewer = request.user.is_authenticated and (
        food.restaurant.owner_id == request.user.id or request.user.role == "admin")
    if not previewer and not (food.is_available and food.restaurant.is_approved):
        raise Http404("Food item not found.")
    related = FoodItem.objects.filter(restaurant=food.restaurant, is_available=True) \
        .exclude(pk=food.pk).select_related("inventory")[:4]
    return render(request, "public/food_detail.html", {"food": food, "related": related})


# ------------------------------------------------------- restaurant owner CRUD
def _owner_or_redirect(request):
    restaurant = owner_restaurant(request.user)
    if restaurant is None:
        messages.info(request, "Please create your restaurant profile first.")
    return restaurant


@role_required("owner")
def manage_food(request):
    restaurant = _owner_or_redirect(request)
    if restaurant is None:
        return redirect("restaurants:profile")
    qs = FoodItem.objects.filter(restaurant=restaurant).select_related("category", "inventory").order_by("name")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(name__icontains=q)
    return render(request, "restaurant/manage_food.html", {"page_obj": paginate(request, qs, 10), "q": q,
                                                           "restaurant": restaurant})


@role_required("owner")
def add_food(request):
    restaurant = _owner_or_redirect(request)
    if restaurant is None:
        return redirect("restaurants:profile")
    is_post = request.method == "POST"
    form = FoodItemForm(request.POST if is_post else None, request.FILES if is_post else None, restaurant=restaurant)
    if is_post and form.is_valid():
        form.save()
        messages.success(request, "Food item added.")
        return redirect("food:manage")
    return render(request, "restaurant/add_food.html", {"form": form, "title": "Add food item"})


@role_required("owner")
def edit_food(request, pk):
    restaurant = _owner_or_redirect(request)
    if restaurant is None:
        return redirect("restaurants:profile")
    food = get_object_or_404(FoodItem, pk=pk, restaurant=restaurant)  # ownership check
    is_post = request.method == "POST"
    form = FoodItemForm(request.POST if is_post else None, request.FILES if is_post else None,
                        instance=food, restaurant=restaurant)
    if is_post and form.is_valid():
        form.save()
        messages.success(request, "Food item updated.")
        return redirect("food:manage")
    return render(request, "restaurant/add_food.html", {"form": form, "title": f"Edit {food.name}", "food": food})


def _owned_food_or_404(request, pk):
    if request.user.role == "admin":
        return get_object_or_404(FoodItem, pk=pk)
    return get_object_or_404(FoodItem, pk=pk, restaurant__owner=request.user)


@role_required("owner", "admin")
@require_POST
def delete_food(request, pk):
    food = _owned_food_or_404(request, pk)
    name = food.name
    try:
        food.delete()
        messages.success(request, f"'{name}' deleted.")
    except Exception:  # protected relations, etc.
        messages.error(request, "This item could not be deleted. Mark it unavailable instead.")
    return redirect("dashboard:manage_food" if request.user.role == "admin" else "food:manage")


@role_required("owner", "admin")
@require_POST
def toggle_availability(request, pk):
    food = _owned_food_or_404(request, pk)
    food.is_available = not food.is_available
    food.save(update_fields=["is_available", "updated_at"])
    messages.success(request, f"'{food.name}' is now {'available' if food.is_available else 'unavailable'}.")
    return redirect("dashboard:manage_food" if request.user.role == "admin" else "food:manage")
