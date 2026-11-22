from django import forms

from inventory.models import Inventory

from .models import FoodCategory, FoodItem


class FoodItemForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=0, initial=0, label="Stock quantity")
    minimum_stock = forms.IntegerField(min_value=0, initial=5, label="Low-stock alert level")

    class Meta:
        model = FoodItem
        fields = ("category", "name", "description", "price", "discount_percent", "image", "is_veg", "is_available")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
        }

    def __init__(self, *args, restaurant, **kwargs):
        super().__init__(*args, **kwargs)
        self.restaurant = restaurant
        self.fields["category"].queryset = FoodCategory.objects.filter(is_active=True)
        if self.instance.pk:
            inventory = getattr(self.instance, "inventory", None)
            if inventory:
                self.fields["quantity"].initial = inventory.quantity
                self.fields["minimum_stock"].initial = inventory.minimum_stock

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicate = FoodItem.objects.filter(restaurant=self.restaurant, name__iexact=name)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("This restaurant already has a food item with that name.")
        return name

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.restaurant = self.restaurant
        if commit:
            obj.save()
            inventory, _ = Inventory.objects.get_or_create(food_item=obj)
            inventory.quantity = self.cleaned_data["quantity"]
            inventory.minimum_stock = self.cleaned_data["minimum_stock"]
            inventory.save()
        return obj
