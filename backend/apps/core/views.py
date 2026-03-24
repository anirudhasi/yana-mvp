import random
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, OTPVerification


@api_view(["POST"])
@permission_classes([AllowAny])
def request_otp(request):
    """Send OTP to phone number. In MVP the OTP is returned in response."""
    phone = request.data.get("phone_number", "").strip()
    if not phone:
        return Response({"error": "phone_number is required"}, status=400)

    otp = str(random.randint(100000, 999999))
    OTPVerification.objects.create(
        phone_number=phone,
        otp=otp,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    # MVP: return OTP in response so you can test without SMS gateway
    payload = {
        "message": f"OTP sent to {phone}",
    }
    if settings.EXPOSE_OTP_IN_RESPONSE:
        payload["otp"] = otp
    return Response(payload)


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    """Verify OTP and return JWT tokens. Creates user if first login."""
    phone = request.data.get("phone_number", "").strip()
    otp   = request.data.get("otp", "").strip()

    if not phone or not otp:
        return Response({"error": "phone_number and otp are required"}, status=400)

    record = OTPVerification.objects.filter(
        phone_number=phone,
        otp=otp,
        is_verified=False,
        expires_at__gte=timezone.now(),
    ).last()

    if not record:
        return Response({"error": "Invalid or expired OTP"}, status=400)

    record.is_verified = True
    record.save()

    user, created = User.objects.get_or_create(
        phone_number=phone,
        defaults={"full_name": phone},
    )

    refresh = RefreshToken.for_user(user)
    return Response({
        "access":  str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id":           str(user.id),
            "phone_number": user.phone_number,
            "full_name":    user.full_name,
            "role":         user.role,
        },
        "is_new_user": created,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Return current authenticated user."""
    u = request.user
    return Response({
        "id":           str(u.id),
        "phone_number": u.phone_number,
        "full_name":    u.full_name,
        "email":        u.email,
        "role":         u.role,
        "is_staff":     u.is_staff,
    })


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update name, email, preferred_language."""
    u = request.user
    for field in ["full_name", "email"]:
        if field in request.data:
            setattr(u, field, request.data[field])
    u.save()
    return Response({"message": "Profile updated"})
