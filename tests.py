from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from core.factories import make_category, make_food, make_restaurant, make_user

from .models import FoodItem


class FoodAPITests(APITestCase):
    def setUp(self):
        self.owner = make_user("o1@example.com", "owner")
        self.other = make_user("o2@example.com", "owner")
        self.customer = make_user("c@example.com", "customer")
        self.restaurant = make_restaurant(self.owner)
        self.category = make_category("Burger")

    def payload(self, **extra):
        data = {"category": self.category.pk, "name": "Veg Burger", "price": "120.00", "stock_quantity": 15}
        data.update(extra)
        return data

    def test_owner_creates_food_with_stock(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(reverse("api-food-list"), self.payload(), format="json")
        self.assertEqual(response.status_code, 201)
        food = FoodItem.objects.get(pk=response.data["id"])
        self.assertEqual(food.restaurant, self.restaurant)
        self.assertEqual(food.inventory.quantity, 15)
        self.assertEqual(response.data["stock"], 15)

    def test_duplicate_name_rejected(self):
        make_food(self.restaurant, name="Veg Burger")
        self.client.force_authenticate(self.owner)
        response = self.client.post(reverse("api-food-list"), self.payload(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_price_rejected(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post(reverse("api-food-list"), self.payload(price="0"), format="json").status_code, 400)

    def test_customer_cannot_create(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post(reverse("api-food-list"), self.payload(), format="json").status_code, 403)

    def test_owner_updates_and_deletes_own_food(self):
        food = make_food(self.restaurant)
        self.client.force_authenticate(self.owner)
        url = reverse("api-food-detail", args=[food.pk])
        response = self.client.patch(url, {"price": "150.00", "stock_quantity": 3}, format="json")
        self.assertEqual(response.status_code, 200)
        food.refresh_from_db()
        self.assertEqual(str(food.price), "150.00")
        self.assertEqual(food.inventory.quantity, 3)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_other_owner_cannot_modify(self):
        food = make_food(self.restaurant)
        make_restaurant(self.other, name="Other Place")
        self.client.force_authenticate(self.other)
        url = reverse("api-food-detail", args=[food.pk])
        self.assertEqual(self.client.patch(url, {"price": "1.00"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)

    def test_public_list_filters_and_hides_unavailable(self):
        make_food(self.restaurant, name="Cheap", price="50.00")
        make_food(self.restaurant, name="Pricey", price="250.00")
        make_food(self.restaurant, name="Hidden", price="60.00", is_available=False)
        response = self.client.get(reverse("api-food-list"))
        self.assertEqual({f["name"] for f in response.data["results"]}, {"Cheap", "Pricey"})
        response = self.client.get(reverse("api-food-list"), {"min_price": 100})
        self.assertEqual([f["name"] for f in response.data["results"]], ["Pricey"])
        response = self.client.get(reverse("api-food-list"), {"search": "cheap"})
        self.assertEqual(len(response.data["results"]), 1)

    def test_category_filter(self):
        other_category = make_category("Pizza")
        make_food(self.restaurant, name="Burger A")
        make_food(self.restaurant, name="Pizza A", category=other_category)
        response = self.client.get(reverse("api-food-list"), {"category": other_category.pk})
        self.assertEqual([f["name"] for f in response.data["results"]], ["Pizza A"])


class FoodWebTests(TestCase):
    def setUp(self):
        self.owner = make_user("o1@example.com", "owner")
        self.restaurant = make_restaurant(self.owner)
        self.category = make_category()

    def test_add_edit_delete_via_forms(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("food:add"), {
            "category": self.category.pk, "name": "Web Burger", "description": "Tasty", "price": "99.50",
            "discount_percent": 10, "is_veg": "on", "is_available": "on", "quantity": 20, "minimum_stock": 5})
        self.assertRedirects(response, reverse("food:manage"), fetch_redirect_response=False)
        food = FoodItem.objects.get(name="Web Burger")
        self.assertEqual(food.inventory.quantity, 20)
        self.assertEqual(str(food.final_price), "89.55")
        response = self.client.post(reverse("food:edit", args=[food.pk]), {
            "category": self.category.pk, "name": "Web Burger", "price": "110.00", "discount_percent": 0,
            "is_available": "on", "quantity": 7, "minimum_stock": 5})
        self.assertEqual(response.status_code, 302)
        food.refresh_from_db()
        self.assertEqual(str(food.price), "110.00")
        self.assertEqual(food.inventory.status, "low_stock")
        self.assertEqual(self.client.post(reverse("food:delete", args=[food.pk])).status_code, 302)
        self.assertFalse(FoodItem.objects.filter(pk=food.pk).exists())

    def test_owner_cannot_edit_other_owners_food(self):
        other = make_restaurant(make_user("o2@example.com", "owner"), name="Other")
        food = make_food(other, name="Secret")
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("food:edit", args=[food.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("food:delete", args=[food.pk])).status_code, 404)

    def test_public_search_and_filters(self):
        make_food(self.restaurant, name="Spicy Burger", price="80.00")
        make_food(self.restaurant, name="Plain Fries", price="40.00", category=make_category("Snacks"))
        response = self.client.get(reverse("food:list"), {"q": "burger"})
        self.assertContains(response, "Spicy Burger")
        self.assertNotContains(response, "Plain Fries")
        response = self.client.get(reverse("food:list"), {"max_price": "50"})
        self.assertContains(response, "Plain Fries")
        self.assertNotContains(response, "Spicy Burger")
        response = self.client.get(reverse("food:list"), {"category": "snacks"})
        self.assertContains(response, "Plain Fries")

    def test_food_detail_renders(self):
        food = make_food(self.restaurant)
        self.assertEqual(self.client.get(reverse("food:detail", args=[food.pk])).status_code, 200)
