"""
Demo data seed script.
Run: python manage.py shell < seed_data.py
Creates: 3 hubs, 6 vehicles, 3 demo riders (applied/kyc_verified/active), 1 allocation.
"""
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yana.settings")
django.setup()

from django.utils import timezone
from apps.core.models import User
from apps.fleet.models import Hub, Vehicle, VehicleAllocation
from apps.onboarding.models import Rider, OnboardingEvent

print("Seeding demo data...")

# ── Admin user ────────────────────────────────────────────────────────────────
admin_user, _ = User.objects.get_or_create(
    phone_number="+919999999999",
    defaults={"full_name": "Yana Admin", "role": "admin", "is_staff": True, "is_superuser": True},
)
admin_user.set_password("admin123")
admin_user.save()
print(f"  Admin: {admin_user.phone_number} / admin123")

# ── Hubs ──────────────────────────────────────────────────────────────────────
hub_data = [
    {"name": "Koramangala Hub",   "city": "Bengaluru"},
    {"name": "HSR Layout Hub",    "city": "Bengaluru"},
    {"name": "Whitefield Hub",    "city": "Bengaluru"},
]
hubs = []
for h in hub_data:
    hub, _ = Hub.objects.get_or_create(name=h["name"], defaults={"city": h["city"], "address": h["name"] + ", Bengaluru"})
    hubs.append(hub)
    print(f"  Hub: {hub.name}")

# ── Vehicles ──────────────────────────────────────────────────────────────────
vehicle_data = [
    {"reg": "KA-01-AB-1234", "model": "Hero Electric Optima",  "hub": hubs[0], "battery": 82, "odo": 12400},
    {"reg": "KA-01-CD-5678", "model": "Bounce Infinity E1",    "hub": hubs[1], "battery": 54, "odo": 8220},
    {"reg": "KA-03-EF-9012", "model": "Ather Rizta",           "hub": hubs[2], "battery": 95, "odo": 3100},
    {"reg": "KA-02-GH-3456", "model": "Hero Electric Photon",  "hub": hubs[0], "battery": 70, "odo": 5600},
    {"reg": "KA-05-IJ-7890", "model": "Ampere Magnus EX",      "hub": hubs[1], "battery": 88, "odo": 9800},
    {"reg": "KA-04-KL-2345", "model": "Ola S1 Pro",            "hub": hubs[2], "battery": 45, "odo": 15000},
]
vehicles = []
for v in vehicle_data:
    veh, _ = Vehicle.objects.get_or_create(
        registration_number=v["reg"],
        defaults={
            "model": v["model"], "manufacturer": v["model"].split()[0],
            "hub": v["hub"], "vehicle_type": "ev_2w",
            "battery_health_pct": v["battery"], "odometer_km": v["odo"],
        },
    )
    vehicles.append(veh)
    print(f"  Vehicle: {veh.registration_number} — {veh.status}")

# ── Demo Riders ───────────────────────────────────────────────────────────────
rider_data = [
    {"phone": "+919876543210", "name": "Ravi Kumar",   "status": "applied",      "hub": hubs[0]},
    {"phone": "+918765432109", "name": "Suresh Patil", "status": "kyc_verified", "hub": hubs[1]},
    {"phone": "+917654321098", "name": "Mohan Das",    "status": "active",       "hub": hubs[2]},
]
riders = []
for r in rider_data:
    user, _ = User.objects.get_or_create(
        phone_number=r["phone"],
        defaults={"full_name": r["name"], "role": "rider"},
    )
    user.set_password("rider123")
    user.save()

    rider, created = Rider.objects.get_or_create(
        user=user,
        defaults={
            "onboarding_status": r["status"],
            "hub": r["hub"],
            "aadhaar_number": "123456789012",
            "dl_number": "KA05-20190123",
            "bank_account": "1234567890",
            "ifsc_code": "SBIN0012345",
            "bank_name": "SBI",
        },
    )
    if r["status"] == "kyc_verified":
        rider.verified_by = admin_user
        rider.verified_at = timezone.now()
        rider.save()
    if r["status"] == "active":
        rider.verified_by  = admin_user
        rider.verified_at  = timezone.now()
        rider.activated_at = timezone.now()
        rider.save()

    riders.append(rider)
    print(f"  Rider: {user.phone_number} ({r['name']}) — {r['status']} / rider123")

# ── Demo allocation (active rider → available vehicle) ────────────────────────
active_rider   = riders[2]   # Mohan Das (active)
alloc_vehicle  = vehicles[2] # Ather Rizta

if not VehicleAllocation.objects.filter(rider=active_rider, status="active").exists():
    from datetime import date
    alloc = VehicleAllocation.objects.create(
        vehicle      = alloc_vehicle,
        rider        = active_rider,
        plan_type    = "daily",
        start_date   = date.today(),
        daily_rent   = 120,
        allocated_by = admin_user,
        notes        = "Demo allocation",
    )
    alloc_vehicle.status = "allocated"
    alloc_vehicle.save()
    print(f"  Allocation: {alloc_vehicle.registration_number} → {active_rider.user.full_name}")

print("\nSeed complete!")
print("\nLogin credentials:")
print("  Admin:  +919999999999 / admin123  → role: admin")
print("  Rider1: +919876543210 / rider123  → status: applied")
print("  Rider2: +918765432109 / rider123  → status: kyc_verified")
print("  Rider3: +917654321098 / rider123  → status: active + vehicle allocated")
