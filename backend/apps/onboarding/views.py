from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Rider, RiderDocument, OnboardingEvent
from .serializers import (
    RiderListSerializer, RiderDetailSerializer,
    RiderProfileUpdateSerializer, DocumentUploadSerializer,
    VerifyRiderSerializer, OnboardingEventSerializer,
)


def _log_event(rider, event_type, from_status, to_status, user, notes=""):
    OnboardingEvent.objects.create(
        rider        = rider,
        event_type   = event_type,
        from_status  = from_status,
        to_status    = to_status,
        performed_by = user,
        notes        = notes,
    )


class RiderViewSet(viewsets.ModelViewSet):
    queryset         = Rider.objects.select_related("user", "hub").prefetch_related("documents")
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ["onboarding_status", "hub"]

    def get_serializer_class(self):
        if self.action == "list":
            return RiderListSerializer
        if self.action in ["update_profile"]:
            return RiderProfileUpdateSerializer
        return RiderDetailSerializer

    # ── Rider creates their own profile ──────────────────────────────────────
    @action(detail=False, methods=["post", "get"])
    def my_profile(self, request):
        """
        GET  /api/onboarding/riders/my_profile/  — fetch my rider profile
        POST /api/onboarding/riders/my_profile/  — create or update my rider profile
        """
        if request.method == "GET":
            try:
                rider = Rider.objects.get(user=request.user)
                return Response(RiderDetailSerializer(rider, context={"request": request}).data)
            except Rider.DoesNotExist:
                return Response({"detail": "No rider profile yet."}, status=404)

        # POST — create or update
        rider, created = Rider.objects.get_or_create(user=request.user)
        s = RiderProfileUpdateSerializer(rider, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()

        if created:
            _log_event(rider, "profile_created", "", rider.onboarding_status, request.user)
        else:
            _log_event(rider, "profile_updated", rider.onboarding_status, rider.onboarding_status, request.user)

        return Response(RiderDetailSerializer(rider, context={"request": request}).data,
                        status=201 if created else 200)

    # ── Document upload ───────────────────────────────────────────────────────
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_document(self, request, pk=None):
        """
        POST /api/onboarding/riders/{id}/upload_document/
        Form-data: doc_type=aadhaar, file=<binary>
        """
        rider = self.get_object()
        s = DocumentUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        doc, _ = RiderDocument.objects.update_or_create(
            rider    = rider,
            doc_type = s.validated_data["doc_type"],
            defaults = {
                "file":                s.validated_data["file"],
                "verification_status": RiderDocument.VerificationStatus.PENDING,
                "rejection_note":      "",
            },
        )

        # Auto-advance status when all 3 mandatory docs are uploaded
        uploaded_types = set(rider.documents.values_list("doc_type", flat=True))
        mandatory      = {"aadhaar", "dl", "photo"}
        if mandatory.issubset(uploaded_types) and rider.onboarding_status == Rider.OnboardingStatus.APPLIED:
            old = rider.onboarding_status
            rider.onboarding_status = Rider.OnboardingStatus.DOCS_SUBMITTED
            rider.save(update_fields=["onboarding_status"])
            _log_event(rider, "docs_submitted", old, rider.onboarding_status, request.user)

        return Response({
            "message":  f"{doc.doc_type} uploaded successfully",
            "doc_id":   str(doc.id),
            "status":   rider.onboarding_status,
        })

    # ── Ops/Admin: approve or reject KYC ─────────────────────────────────────
    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """
        POST /api/onboarding/riders/{id}/verify/
        Body: { "action": "approve" } or { "action": "reject", "rejection_reason": "..." }
        """
        rider = self.get_object()
        s = VerifyRiderSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        old_status = rider.onboarding_status

        if s.validated_data["action"] == "approve":
            rider.onboarding_status = Rider.OnboardingStatus.KYC_VERIFIED
            rider.verified_by       = request.user
            rider.verified_at       = timezone.now()
            rider.rejection_reason  = ""
            note = "KYC approved by ops team"
        else:
            reason = s.validated_data.get("rejection_reason", "")
            rider.onboarding_status = Rider.OnboardingStatus.REJECTED
            rider.rejection_reason  = reason
            note = reason

        rider.save()
        _log_event(rider, "kyc_decision", old_status, rider.onboarding_status, request.user, note)

        return Response({
            "message": f"Rider {s.validated_data['action']}d",
            "status":  rider.onboarding_status,
        })

    # ── Ops/Admin: activate rider (after KYC verified) ────────────────────────
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """POST /api/onboarding/riders/{id}/activate/"""
        rider = self.get_object()
        if rider.onboarding_status != Rider.OnboardingStatus.KYC_VERIFIED:
            return Response(
                {"error": f"Cannot activate. Current status: {rider.onboarding_status}. Must be kyc_verified first."},
                status=400,
            )
        old = rider.onboarding_status
        rider.onboarding_status = Rider.OnboardingStatus.ACTIVE
        rider.activated_at      = timezone.now()
        rider.save()
        _log_event(rider, "activated", old, rider.onboarding_status, request.user)
        return Response({"message": "Rider activated", "status": "active"})

    # ── Audit trail ───────────────────────────────────────────────────────────
    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        """GET /api/onboarding/riders/{id}/events/"""
        rider  = self.get_object()
        events = rider.events.all()
        return Response(OnboardingEventSerializer(events, many=True).data)

    # ── Stats for dashboard ───────────────────────────────────────────────────
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """GET /api/onboarding/riders/stats/"""
        from django.db.models import Count
        data = Rider.objects.values("onboarding_status").annotate(count=Count("id"))
        total = Rider.objects.count()
        return Response({"total": total, "by_status": list(data)})
