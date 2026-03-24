import uuid
from django.db import models
from django.conf import settings


class Hub(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name      = models.CharField(max_length=200)
    city      = models.CharField(max_length=100)
    address   = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hubs"

    def __str__(self):
        return f"{self.name} — {self.city}"


class Vehicle(models.Model):
    class Status(models.TextChoices):
        AVAILABLE   = "available",   "Available"
        ALLOCATED   = "allocated",   "Allocated"
        MAINTENANCE = "maintenance", "In Maintenance"
        RETIRED     = "retired",     "Retired"

    class VehicleType(models.TextChoices):
        EV_2W = "ev_2w", "2-Wheeler EV"
        EV_3W = "ev_3w", "3-Wheeler EV"

    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration_number = models.CharField(max_length=20, unique=True)
    model               = models.CharField(max_length=100)
    manufacturer        = models.CharField(max_length=100, blank=True)
    vehicle_type        = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.EV_2W)
    hub                 = models.ForeignKey(Hub, on_delete=models.PROTECT, related_name="vehicles")
    status              = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    battery_health_pct  = models.FloatField(default=100.0)
    odometer_km         = models.FloatField(default=0.0)
    notes               = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vehicles"

    def __str__(self):
        return f"{self.registration_number} ({self.model})"


class VehicleAllocation(models.Model):
    class PlanType(models.TextChoices):
        DAILY   = "daily",   "Daily Rental"
        WEEKLY  = "weekly",  "Weekly Rental"
        MONTHLY = "monthly", "Monthly Rental"

    class AllocationStatus(models.TextChoices):
        ACTIVE    = "active",    "Active"
        RETURNED  = "returned",  "Returned"
        CANCELLED = "cancelled", "Cancelled"

    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle            = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="allocations")
    rider              = models.ForeignKey("onboarding.Rider", on_delete=models.PROTECT, related_name="allocations")
    plan_type          = models.CharField(max_length=20, choices=PlanType.choices)
    start_date         = models.DateField()
    end_date           = models.DateField(null=True, blank=True)
    actual_return_date = models.DateField(null=True, blank=True)
    daily_rent         = models.DecimalField(max_digits=10, decimal_places=2)
    status             = models.CharField(max_length=20, choices=AllocationStatus.choices, default=AllocationStatus.ACTIVE)
    allocated_by       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    notes              = models.TextField(blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vehicle_allocations"

    def __str__(self):
        return f"{self.vehicle.registration_number} → {self.rider.user.full_name}"
