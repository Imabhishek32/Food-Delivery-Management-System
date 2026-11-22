from django.urls import path

from . import views

app_name = "food"

urlpatterns = [
    path("", views.food_list, name="list"),
    path("manage/", views.manage_food, name="manage"),
    path("manage/add/", views.add_food, name="add"),
    path("manage/<int:pk>/edit/", views.edit_food, name="edit"),
    path("manage/<int:pk>/delete/", views.delete_food, name="delete"),
    path("manage/<int:pk>/toggle/", views.toggle_availability, name="toggle"),
    path("<int:pk>/", views.food_detail, name="detail"),
]
