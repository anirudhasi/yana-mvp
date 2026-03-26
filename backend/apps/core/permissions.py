from rest_framework.permissions import BasePermission


INTERNAL_ROLES = {"admin", "ops", "sales"}
OPS_ROLES = {"admin", "ops"}


def user_role(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "role", None)


def is_internal_user(user):
    return user_role(user) in INTERNAL_ROLES


def is_ops_user(user):
    return user_role(user) in OPS_ROLES


class IsInternalUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and is_internal_user(request.user))


class IsOpsUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and is_ops_user(request.user))
