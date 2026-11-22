from rest_framework.routers import SimpleRouter

from .api_views import FoodItemViewSet

router = SimpleRouter()
router.register("foods", FoodItemViewSet, basename="api-food")

urlpatterns = router.urls
