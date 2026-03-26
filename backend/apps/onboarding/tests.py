from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.models import User
from apps.fleet.models import Hub, Vehicle
from apps.onboarding.models import Rider


class RiderServiceFlowTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone_number="+910000000001",
            password="admin123",
            full_name="Admin User",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.ops = User.objects.create_user(
            phone_number="+910000000002",
            password="ops123",
            full_name="Ops User",
            role=User.Role.OPS,
        )
        self.rider_user = User.objects.create_user(
            phone_number="+910000000003",
            password="rider123",
            full_name="Rider User",
            role=User.Role.RIDER,
        )
        self.other_rider_user = User.objects.create_user(
            phone_number="+910000000004",
            password="rider123",
            full_name="Other Rider",
            role=User.Role.RIDER,
        )

        self.hub = Hub.objects.create(name="Main Hub", city="Bengaluru")
        self.rider = Rider.objects.create(user=self.rider_user, hub=self.hub)
        self.other_rider = Rider.objects.create(user=self.other_rider_user, hub=self.hub)
        self.vehicle = Vehicle.objects.create(
            registration_number="KA-01-AA-1234",
            model="Test EV",
            manufacturer="Test",
            hub=self.hub,
            status=Vehicle.Status.AVAILABLE,
        )

    def test_rider_list_is_scoped_to_self(self):
        self.client.force_authenticate(self.rider_user)

        response = self.client.get("/api/onboarding/riders/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["phone_number"], self.rider_user.phone_number)

    def test_rider_cannot_upload_document_for_other_rider(self):
        self.client.force_authenticate(self.rider_user)

        response = self.client.post(
            f"/api/onboarding/riders/{self.other_rider.id}/upload_document/",
            {
                "doc_type": "aadhaar",
                "file": SimpleUploadedFile("aadhaar.txt", b"test document"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ops_cannot_approve_kyc_without_required_documents(self):
        self.client.force_authenticate(self.ops)
        self.rider.onboarding_status = Rider.OnboardingStatus.DOCS_SUBMITTED
        self.rider.save(update_fields=["onboarding_status"])

        response = self.client.post(
            f"/api/onboarding/riders/{self.rider.id}/verify/",
            {"action": "approve"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot approve KYC", response.data["error"])

    def test_internal_user_can_create_rider_without_otp(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/onboarding/riders/create_rider/",
            {
                "phone_number": "+910000000099",
                "full_name": "New Rider",
                "hub": str(self.hub.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["phone_number"], "+910000000099")
        self.assertEqual(str(response.data["hub"]), str(self.hub.id))

    def test_only_active_rider_can_be_allocated(self):
        self.client.force_authenticate(self.ops)

        first = self.client.post(
            "/api/fleet/allocations/allocate/",
            {
                "vehicle_id": str(self.vehicle.id),
                "rider_id": str(self.rider.id),
                "plan_type": "daily",
                "start_date": str(date.today()),
                "daily_rent": "100.00",
            },
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_400_BAD_REQUEST)

        self.rider.onboarding_status = Rider.OnboardingStatus.ACTIVE
        self.rider.save(update_fields=["onboarding_status"])

        second = self.client.post(
            "/api/fleet/allocations/allocate/",
            {
                "vehicle_id": str(self.vehicle.id),
                "rider_id": str(self.rider.id),
                "plan_type": "daily",
                "start_date": str(date.today()),
                "daily_rent": "100.00",
            },
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
