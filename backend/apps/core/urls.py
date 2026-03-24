from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("otp/request/",   views.request_otp,    name="otp-request"),
    path("otp/verify/",    views.verify_otp,      name="otp-verify"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/",            views.me,              name="me"),
    path("me/update/",     views.update_profile,  name="me-update"),
]
