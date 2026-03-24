from django.contrib import admin
from .models import Rider, RiderDocument, OnboardingEvent


class RiderDocumentInline(admin.TabularInline):
    model  = RiderDocument
    extra  = 0
    fields = ["doc_type", "file", "verification_status", "rejection_note"]
    readonly_fields = ["uploaded_at"]


class OnboardingEventInline(admin.TabularInline):
    model      = OnboardingEvent
    extra      = 0
    readonly_fields = ["event_type", "from_status", "to_status", "performed_by", "notes", "created_at"]
    can_delete = False


@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display   = ["__str__", "onboarding_status", "hub", "verified_at", "created_at"]
    list_filter    = ["onboarding_status", "hub"]
    search_fields  = ["user__full_name", "user__phone_number", "aadhaar_number", "dl_number"]
    readonly_fields = ["created_at", "updated_at", "verified_at", "activated_at"]
    inlines        = [RiderDocumentInline, OnboardingEventInline]
    actions        = ["approve_kyc", "reject_kyc", "activate_riders"]

    @admin.action(description="Approve KYC for selected riders")
    def approve_kyc(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(onboarding_status__in=["docs_submitted", "kyc_pending"]).update(
            onboarding_status="kyc_verified",
            verified_by=request.user,
            verified_at=timezone.now(),
        )
        self.message_user(request, f"{updated} rider(s) KYC approved.")

    @admin.action(description="Mark selected riders as Active")
    def activate_riders(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(onboarding_status="kyc_verified").update(
            onboarding_status="active",
            activated_at=timezone.now(),
        )
        self.message_user(request, f"{updated} rider(s) activated.")

    @admin.action(description="Reject selected riders")
    def reject_kyc(self, request, queryset):
        updated = queryset.exclude(onboarding_status="active").update(
            onboarding_status="rejected",
        )
        self.message_user(request, f"{updated} rider(s) rejected.")


@admin.register(RiderDocument)
class RiderDocumentAdmin(admin.ModelAdmin):
    list_display  = ["rider", "doc_type", "verification_status", "uploaded_at"]
    list_filter   = ["doc_type", "verification_status"]
    search_fields = ["rider__user__full_name"]


@admin.register(OnboardingEvent)
class OnboardingEventAdmin(admin.ModelAdmin):
    list_display = ["rider", "event_type", "from_status", "to_status", "performed_by", "created_at"]
    list_filter  = ["event_type"]
    readonly_fields = ["rider", "event_type", "from_status", "to_status", "performed_by", "notes", "created_at"]
