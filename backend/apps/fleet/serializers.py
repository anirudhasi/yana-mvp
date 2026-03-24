from rest_framework import serializers
from .models import Hub, Vehicle, VehicleAllocation


class HubSerializer(serializers.ModelSerializer):
    vehicle_count = serializers.IntegerField(source="vehicles.count", read_only=True)

    class Meta:
        model  = Hub
        fields = ["id", "name", "city", "address", "is_active", "vehicle_count", "created_at"]


class VehicleSerializer(serializers.ModelSerializer):
    hub_name = serializers.CharField(source="hub.name", read_only=True)
    hub_city = serializers.CharField(source="hub.city", read_only=True)

    class Meta:
        model  = Vehicle
        fields = [
            "id", "registration_number", "model", "manufacturer",
            "vehicle_type", "hub", "hub_name", "hub_city",
            "status", "battery_health_pct", "odometer_km",
            "notes", "created_at", "updated_at",
        ]


class VehicleAllocationSerializer(serializers.ModelSerializer):
    vehicle_reg  = serializers.CharField(source="vehicle.registration_number", read_only=True)
    vehicle_model = serializers.CharField(source="vehicle.model", read_only=True)
    rider_name   = serializers.CharField(source="rider.user.full_name", read_only=True)
    rider_phone  = serializers.CharField(source="rider.user.phone_number", read_only=True)

    class Meta:
        model  = VehicleAllocation
        fields = [
            "id", "vehicle", "vehicle_reg", "vehicle_model",
            "rider", "rider_name", "rider_phone",
            "plan_type", "start_date", "end_date", "actual_return_date",
            "daily_rent", "status", "notes", "created_at",
        ]


class AllocateSerializer(serializers.Serializer):
    vehicle_id = serializers.UUIDField()
    rider_id   = serializers.UUIDField()
    plan_type  = serializers.ChoiceField(choices=VehicleAllocation.PlanType.choices)
    start_date = serializers.DateField()
    end_date   = serializers.DateField(required=False, allow_null=True)
    daily_rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    notes      = serializers.CharField(required=False, allow_blank=True)
