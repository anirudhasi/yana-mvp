from django.contrib import admin
from .models import Hub, Vehicle, VehicleAllocation


@admin.register(Hub)
class HubAdmin(admin.ModelAdmin):
    list_display  = ["name", "city", "is_active", "created_at"]
    list_filter   = ["city", "is_active"]
    search_fields = ["name", "city"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display  = ["registration_number", "model", "hub", "status", "battery_health_pct", "odometer_km"]
    list_filter   = ["status", "vehicle_type", "hub"]
    search_fields = ["registration_number", "model"]
    list_editable = ["status", "battery_health_pct"]


@admin.register(VehicleAllocation)
class VehicleAllocationAdmin(admin.ModelAdmin):
    list_display  = ["vehicle", "rider", "plan_type", "start_date", "daily_rent", "status"]
    list_filter   = ["status", "plan_type"]
    search_fields = ["vehicle__registration_number", "rider__user__full_name"]
    raw_id_fields = ["vehicle", "rider"]
