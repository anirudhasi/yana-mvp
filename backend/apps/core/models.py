import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra):
        if not phone_number:
            raise ValueError("Phone number required")
        user = self.model(phone_number=phone_number, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra):
        extra.setdefault("role", "admin")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(phone_number, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        RIDER  = "rider",  "Rider"
        OPS    = "ops",    "Fleet Ops"
        SALES  = "sales",  "Sales"
        ADMIN  = "admin",  "Admin"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, unique=True)
    full_name    = models.CharField(max_length=200, blank=True)
    email        = models.EmailField(blank=True)
    role         = models.CharField(max_length=20, choices=Role.choices, default=Role.RIDER)
    is_active    = models.BooleanField(default=True)
    is_staff     = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD  = "phone_number"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"


class OTPVerification(models.Model):
    phone_number = models.CharField(max_length=15)
    otp          = models.CharField(max_length=6)
    is_verified  = models.BooleanField(default=False)
    expires_at   = models.DateTimeField()
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_verifications"
        ordering = ["-created_at"]
