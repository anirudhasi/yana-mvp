from rest_framework import serializers
from .models import Rider, RiderDocument, OnboardingEvent


class RiderDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model  = RiderDocument
        fields = ["id", "doc_type", "file_url", "verification_status",
                  "rejection_note", "uploaded_at", "verified_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class RiderListSerializer(serializers.ModelSerializer):
    full_name    = serializers.CharField(source="user.full_name", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    hub_name     = serializers.CharField(source="hub.name", read_only=True)

    class Meta:
        model  = Rider
        fields = ["id", "full_name", "phone_number", "onboarding_status",
                  "hub_name", "created_at"]


class RiderDetailSerializer(serializers.ModelSerializer):
    full_name    = serializers.CharField(source="user.full_name", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    email        = serializers.CharField(source="user.email", read_only=True)
    hub_name     = serializers.CharField(source="hub.name", read_only=True)
    documents    = RiderDocumentSerializer(many=True, read_only=True)

    class Meta:
        model  = Rider
        fields = [
            "id", "full_name", "phone_number", "email",
            "aadhaar_number", "dl_number", "dl_expiry",
            "bank_account", "ifsc_code", "bank_name",
            "onboarding_status", "rejection_reason",
            "hub", "hub_name", "documents",
            "verified_at", "activated_at",
            "created_at", "updated_at",
        ]


class RiderProfileUpdateSerializer(serializers.ModelSerializer):
    """Rider fills in their own KYC details."""
    class Meta:
        model  = Rider
        fields = ["aadhaar_number", "dl_number", "dl_expiry",
                  "bank_account", "ifsc_code", "bank_name", "hub"]


class DocumentUploadSerializer(serializers.Serializer):
    doc_type = serializers.ChoiceField(choices=RiderDocument.DocType.choices)
    file     = serializers.FileField()


class VerifyRiderSerializer(serializers.Serializer):
    action           = serializers.ChoiceField(choices=["approve", "reject"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class OnboardingEventSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source="performed_by.full_name", read_only=True)

    class Meta:
        model  = OnboardingEvent
        fields = ["id", "event_type", "from_status", "to_status",
                  "performed_by_name", "notes", "created_at"]
