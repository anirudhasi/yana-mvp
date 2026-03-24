from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Hub, Vehicle, VehicleAllocation
from .serializers import HubSerializer, VehicleSerializer, VehicleAllocationSerializer, AllocateSerializer


class HubViewSet(viewsets.ModelViewSet):
    queryset         = Hub.objects.all()
    serializer_class = HubSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ["city", "is_active"]


class VehicleViewSet(viewsets.ModelViewSet):
    queryset         = Vehicle.objects.select_related("hub").all()
    serializer_class = VehicleSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ["status", "hub", "vehicle_type"]

    @action(detail=False, methods=["get"])
    def available(self, request):
        """Quick endpoint: GET /api/fleet/vehicles/available/?hub=<id>"""
        qs = Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE).select_related("hub")
        hub = request.query_params.get("hub")
        if hub:
            qs = qs.filter(hub=hub)
        return Response(VehicleSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Fleet status summary."""
        from django.db.models import Count
        data = Vehicle.objects.values("status").annotate(count=Count("id"))
        return Response(list(data))


class VehicleAllocationViewSet(viewsets.ModelViewSet):
    queryset         = VehicleAllocation.objects.select_related("vehicle", "rider__user").all()
    serializer_class = VehicleAllocationSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ["status", "vehicle", "rider"]

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def allocate(self, request):
        """
        Allocate an available vehicle to an active rider.
        POST /api/fleet/allocations/allocate/
        Body: { vehicle_id, rider_id, plan_type, start_date, daily_rent }
        """
        s = AllocateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        # Lock vehicle row to prevent race conditions
        try:
            vehicle = Vehicle.objects.select_for_update().get(id=d["vehicle_id"])
        except Vehicle.DoesNotExist:
            return Response({"error": "Vehicle not found"}, status=404)

        from apps.onboarding.models import Rider
        try:
            rider = Rider.objects.get(id=d["rider_id"])
        except Rider.DoesNotExist:
            return Response({"error": "Rider not found"}, status=404)

        if vehicle.status != Vehicle.Status.AVAILABLE:
            return Response({"error": f"Vehicle is {vehicle.status}, not available"}, status=400)

        if rider.onboarding_status != "active":
            return Response({"error": f"Rider status is '{rider.onboarding_status}'. Must be 'active' to allocate a vehicle."}, status=400)

        if rider.allocations.filter(status="active").exists():
            return Response({"error": "Rider already has an active vehicle allocation"}, status=400)

        allocation = VehicleAllocation.objects.create(
            vehicle      = vehicle,
            rider        = rider,
            plan_type    = d["plan_type"],
            start_date   = d["start_date"],
            end_date     = d.get("end_date"),
            daily_rent   = d["daily_rent"],
            allocated_by = request.user,
            notes        = d.get("notes", ""),
        )

        vehicle.status = Vehicle.Status.ALLOCATED
        vehicle.save(update_fields=["status", "updated_at"])

        return Response(VehicleAllocationSerializer(allocation).data, status=201)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def return_vehicle(self, request, pk=None):
        """
        Return a vehicle from an active allocation.
        POST /api/fleet/allocations/{id}/return_vehicle/
        """
        allocation = self.get_object()
        if allocation.status != VehicleAllocation.AllocationStatus.ACTIVE:
            return Response({"error": "Allocation is not active"}, status=400)

        allocation.status             = VehicleAllocation.AllocationStatus.RETURNED
        allocation.actual_return_date = timezone.now().date()
        allocation.save()

        allocation.vehicle.status = Vehicle.Status.AVAILABLE
        allocation.vehicle.save(update_fields=["status", "updated_at"])

        return Response({"message": "Vehicle returned successfully", "status": "returned"})
