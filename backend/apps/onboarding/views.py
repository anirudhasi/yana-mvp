from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import User
from apps.core.permissions import is_internal_user, is_ops_user

from .models import OnboardingEvent, Rider, RiderDocument
from .serializers import (
    DocumentUploadSerializer,
    OnboardingEventSerializer,
    RiderDetailSerializer,
    RiderListSerializer,
    RiderProfileUpdateSerializer,
    StaffCreateRiderSerializer,
    VerifyRiderSerializer,
)


def _log_event(rider, event_type, from_status, to_status, user, notes=""):
    OnboardingEvent.objects.create(
        rider=rider,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        performed_by=user,
        notes=notes,
    )


class RiderViewSet(viewsets.ModelViewSet):
    queryset = Rider.objects.select_related("user", "hub").prefetch_related("documents")
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["onboarding_status", "hub"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if is_internal_user(self.request.user):
            return qs
        if getattr(self.request.user, "role", None) == User.Role.RIDER:
            return qs.filter(user=self.request.user)
        return qs.none()

    def get_serializer_class(self):
        if self.action == "list":
            return RiderListSerializer
        if self.action == "create_rider":
            return StaffCreateRiderSerializer
        if self.action == "update_profile":
            return RiderProfileUpdateSerializer
        return RiderDetailSerializer

    def _can_access_rider(self, rider):
        return is_internal_user(self.request.user) or rider.user_id == self.request.user.id

    def _mandatory_docs_uploaded(self, rider):
        uploaded_types = set(rider.documents.values_list("doc_type", flat=True))
        return {"aadhaar", "dl", "photo"}.issubset(uploaded_types)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def create_rider(self, request):
        if not is_internal_user(request.user):
            return Response({"detail": "Only internal users can create riders."}, status=status.HTTP_403_FORBIDDEN)

        serializer = StaffCreateRiderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user, user_created = User.objects.get_or_create(
            phone_number=data["phone_number"],
            defaults={
                "full_name": data["full_name"],
                "email": data.get("email", ""),
                "role": User.Role.RIDER,
            },
        )
        if not user_created:
            user.full_name = data["full_name"]
            user.email = data.get("email", user.email)
            user.role = User.Role.RIDER
            user.save(update_fields=["full_name", "email", "role"])

        rider, rider_created = Rider.objects.get_or_create(
            user=user,
            defaults={"hub": data.get("hub")},
        )
        if not rider_created and "hub" in data:
            rider.hub = data.get("hub")
            rider.save(update_fields=["hub", "updated_at"])

        _log_event(
            rider,
            "staff_created" if rider_created else "staff_updated",
            "",
            rider.onboarding_status,
            request.user,
            "Rider profile created by internal team",
        )

        return Response(
            RiderDetailSerializer(rider, context={"request": request}).data,
            status=status.HTTP_201_CREATED if rider_created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post", "get"])
    def my_profile(self, request):
        if request.method == "GET":
            try:
                rider = Rider.objects.get(user=request.user)
                return Response(RiderDetailSerializer(rider, context={"request": request}).data)
            except Rider.DoesNotExist:
                return Response({"detail": "No rider profile yet."}, status=status.HTTP_404_NOT_FOUND)

        rider, created = Rider.objects.get_or_create(user=request.user)
        serializer = RiderProfileUpdateSerializer(rider, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if created:
            _log_event(rider, "profile_created", "", rider.onboarding_status, request.user)
        else:
            _log_event(rider, "profile_updated", rider.onboarding_status, rider.onboarding_status, request.user)

        return Response(
            RiderDetailSerializer(rider, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_document(self, request, pk=None):
        rider = self.get_object()
        if not self._can_access_rider(rider):
            return Response(
                {"detail": "You do not have permission to upload documents for this rider."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc, _ = RiderDocument.objects.update_or_create(
            rider=rider,
            doc_type=serializer.validated_data["doc_type"],
            defaults={
                "file": serializer.validated_data["file"],
                "verification_status": RiderDocument.VerificationStatus.PENDING,
                "rejection_note": "",
            },
        )

        if self._mandatory_docs_uploaded(rider) and rider.onboarding_status == Rider.OnboardingStatus.APPLIED:
            old_status = rider.onboarding_status
            rider.onboarding_status = Rider.OnboardingStatus.DOCS_SUBMITTED
            rider.save(update_fields=["onboarding_status"])
            _log_event(rider, "docs_submitted", old_status, rider.onboarding_status, request.user)

        return Response(
            {
                "message": f"{doc.doc_type} uploaded successfully",
                "doc_id": str(doc.id),
                "status": rider.onboarding_status,
            }
        )

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        if not is_ops_user(request.user):
            return Response({"detail": "Only ops/admin users can verify rider KYC."}, status=status.HTTP_403_FORBIDDEN)

        rider = self.get_object()
        serializer = VerifyRiderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = rider.onboarding_status
        action_name = serializer.validated_data["action"]

        if action_name == "approve":
            if rider.onboarding_status not in {
                Rider.OnboardingStatus.DOCS_SUBMITTED,
                Rider.OnboardingStatus.KYC_PENDING,
            }:
                return Response(
                    {"error": f"Cannot approve rider from status '{rider.onboarding_status}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not self._mandatory_docs_uploaded(rider):
                return Response(
                    {"error": "Cannot approve KYC until Aadhaar, DL, and photo documents are uploaded."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            rider.onboarding_status = Rider.OnboardingStatus.KYC_VERIFIED
            rider.verified_by = request.user
            rider.verified_at = timezone.now()
            rider.rejection_reason = ""
            note = "KYC approved by ops team"
        else:
            if rider.onboarding_status == Rider.OnboardingStatus.ACTIVE:
                return Response({"error": "Cannot reject an active rider."}, status=status.HTTP_400_BAD_REQUEST)

            note = serializer.validated_data["rejection_reason"]
            rider.onboarding_status = Rider.OnboardingStatus.REJECTED
            rider.rejection_reason = note

        rider.save()
        _log_event(rider, "kyc_decision", old_status, rider.onboarding_status, request.user, note)

        return Response({"message": f"Rider {action_name}d", "status": rider.onboarding_status})

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        if not is_ops_user(request.user):
            return Response({"detail": "Only ops/admin users can activate riders."}, status=status.HTTP_403_FORBIDDEN)

        rider = self.get_object()
        if rider.onboarding_status != Rider.OnboardingStatus.KYC_VERIFIED:
            return Response(
                {"error": f"Cannot activate. Current status: {rider.onboarding_status}. Must be kyc_verified first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = rider.onboarding_status
        rider.onboarding_status = Rider.OnboardingStatus.ACTIVE
        rider.activated_at = timezone.now()
        rider.save()
        _log_event(rider, "activated", old_status, rider.onboarding_status, request.user)
        return Response({"message": "Rider activated", "status": "active"})

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        rider = self.get_object()
        if not self._can_access_rider(rider):
            return Response(
                {"detail": "You do not have permission to view this rider's events."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(OnboardingEventSerializer(rider.events.all(), many=True).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        if not is_internal_user(request.user):
            return Response({"detail": "Only internal users can view rider stats."}, status=status.HTTP_403_FORBIDDEN)

        from django.db.models import Count

        data = Rider.objects.values("onboarding_status").annotate(count=Count("id"))
        return Response({"total": Rider.objects.count(), "by_status": list(data)})
