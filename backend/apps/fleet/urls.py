from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HubViewSet, VehicleViewSet, VehicleAllocationViewSet

router = DefaultRouter()
router.register("hubs",        HubViewSet,              basename="hub")
router.register("vehicles",    VehicleViewSet,           basename="vehicle")
router.register("allocations", VehicleAllocationViewSet, basename="allocation")

urlpatterns = [path("", include(router.urls))]
