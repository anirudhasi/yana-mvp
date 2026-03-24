import uuid
from django.db import models
from django.conf import settings


class Rider(models.Model):
    class OnboardingStatus(models.TextChoices):
        APPLIED          = "applied",          "Applied"
        DOCS_SUBMITTED   = "docs_submitted",   "Documents Submitted"
        KYC_PENDING      = "kyc_pending",      "KYC Pending"
        KYC_VERIFIED     = "kyc_verified",     "KYC Verified"
        ACTIVE           = "active",           "Active"
        REJECTED         = "rejected",         "Rejected"
        SUSPENDED        = "suspended",        "Suspended"

    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user              = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rider_profile")
    aadhaar_number    = models.CharField(max_length=12, blank=True)
    dl_number         = models.CharField(max_length=20, blank=True)
    dl_expiry         = models.DateField(null=True, blank=True)
    bank_account      = models.CharField(max_length=20, blank=True)
    ifsc_code         = models.CharField(max_length=11, blank=True)
    bank_name         = models.CharField(max_length=100, blank=True)
    onboarding_status = models.CharField(max_length=30, choices=OnboardingStatus.choices, default=OnboardingStatus.APPLIED)
    rejection_reason  = models.TextField(blank=True)
    hub               = models.ForeignKey("fleet.Hub", null=True, blank=True, on_delete=models.SET_NULL, related_name="riders")
    verified_by       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_riders")
    verified_at       = models.DateTimeField(null=True, blank=True)
    activated_at      = models.DateTimeField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "riders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.full_name} — {self.onboarding_status}"


class RiderDocument(models.Model):
    class DocType(models.TextChoices):
        AADHAAR      = "aadhaar",       "Aadhaar Card"
        DL           = "dl",            "Driving License"
        BANK_PASSBOOK = "bank_passbook", "Bank Passbook"
        PHOTO        = "photo",         "Passport Photo"

    class VerificationStatus(models.TextChoices):
        PENDING  = "pending",  "Pending Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider               = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="documents")
    doc_type            = models.CharField(max_length=30, choices=DocType.choices)
    file                = models.FileField(upload_to="rider_docs/%Y/%m/")
    verification_status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    rejection_note      = models.TextField(blank=True)
    verified_by         = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_docs")
    verified_at         = models.DateTimeField(null=True, blank=True)
    uploaded_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table      = "rider_documents"
        unique_together = [("rider", "doc_type")]

    def __str__(self):
        return f"{self.rider.user.full_name} — {self.doc_type}"


class OnboardingEvent(models.Model):
    """Immutable audit trail — one row per status change."""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider        = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="events")
    event_type   = models.CharField(max_length=50)
    from_status  = models.CharField(max_length=30, blank=True)
    to_status    = models.CharField(max_length=30, blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "onboarding_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rider} | {self.event_type} @ {self.created_at:%Y-%m-%d %H:%M}"
