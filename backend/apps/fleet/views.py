from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import is_ops_user

from .models import Hub, Vehicle, VehicleAllocation
from .serializers import AllocateSerializer, HubSerializer, VehicleAllocationSerializer, VehicleSerializer


class HubViewSet(viewsets.ModelViewSet):
    queryset = Hub.objects.all()
    serializer_class = HubSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["city", "is_active"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not is_ops_user(self.request.user):
            return Hub.objects.none()
        return super().get_queryset()


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.select_related("hub").all()
    serializer_class = VehicleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "hub", "vehicle_type"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not is_ops_user(self.request.user):
            return Vehicle.objects.none()
        return super().get_queryset()

    @action(detail=False, methods=["get"])
    def available(self, request):
        if not is_ops_user(request.user):
            return Response({"detail": "Only ops/admin users can view available vehicles."}, status=status.HTTP_403_FORBIDDEN)

        qs = Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE).select_related("hub")
        hub = request.query_params.get("hub")
        if hub:
            qs = qs.filter(hub=hub)
        return Response(VehicleSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        if not is_ops_user(request.user):
            return Response({"detail": "Only ops/admin users can view fleet stats."}, status=status.HTTP_403_FORBIDDEN)

        from django.db.models import Count

        data = Vehicle.objects.values("status").annotate(count=Count("id"))
        return Response(list(data))


class VehicleAllocationViewSet(viewsets.ModelViewSet):
    queryset = VehicleAllocation.objects.select_related("vehicle", "rider__user").all()
    serializer_class = VehicleAllocationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "vehicle", "rider"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not is_ops_user(self.request.user):
            return VehicleAllocation.objects.none()
        return super().get_queryset()

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def allocate(self, request):
        if not is_ops_user(request.user):
            return Response({"detail": "Only ops/admin users can allocate vehicles."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AllocateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            vehicle = Vehicle.objects.select_for_update().get(id=data["vehicle_id"])
        except Vehicle.DoesNotExist:
            return Response({"error": "Vehicle not found"}, status=status.HTTP_404_NOT_FOUND)

        from apps.onboarding.models import Rider

        try:
            rider = Rider.objects.get(id=data["rider_id"])
        except Rider.DoesNotExist:
            return Response({"error": "Rider not found"}, status=status.HTTP_404_NOT_FOUND)

        if vehicle.status != Vehicle.Status.AVAILABLE:
            return Response({"error": f"Vehicle is {vehicle.status}, not available"}, status=status.HTTP_400_BAD_REQUEST)
        if rider.onboarding_status != "active":
            return Response(
                {"error": f"Rider status is '{rider.onboarding_status}'. Must be 'active' to allocate a vehicle."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if rider.allocations.filter(status="active").exists():
            return Response({"error": "Rider already has an active vehicle allocation"}, status=status.HTTP_400_BAD_REQUEST)

        allocation = VehicleAllocation.objects.create(
            vehicle=vehicle,
            rider=rider,
            plan_type=data["plan_type"],
            start_date=data["start_date"],
            end_date=data.get("end_date"),
            daily_rent=data["daily_rent"],
            allocated_by=request.user,
            notes=data.get("notes", ""),
        )

        vehicle.status = Vehicle.Status.ALLOCATED
        vehicle.save(update_fields=["status", "updated_at"])

        return Response(VehicleAllocationSerializer(allocation).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def return_vehicle(self, request, pk=None):
        if not is_ops_user(request.user):
            return Response({"detail": "Only ops/admin users can return vehicles."}, status=status.HTTP_403_FORBIDDEN)

        allocation = self.get_object()
        if allocation.status != VehicleAllocation.AllocationStatus.ACTIVE:
            return Response({"error": "Allocation is not active"}, status=status.HTTP_400_BAD_REQUEST)

        allocation.status = VehicleAllocation.AllocationStatus.RETURNED
        allocation.actual_return_date = timezone.now().date()
        allocation.save()

        allocation.vehicle.status = Vehicle.Status.AVAILABLE
        allocation.vehicle.save(update_fields=["status", "updated_at"])

        return Response({"message": "Vehicle returned successfully", "status": "returned"})
