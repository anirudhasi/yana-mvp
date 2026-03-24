from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RiderViewSet

router = DefaultRouter()
router.register("riders", RiderViewSet, basename="rider")

urlpatterns = [path("", include(router.urls))]
