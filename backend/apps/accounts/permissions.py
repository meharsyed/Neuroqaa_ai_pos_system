"""
Role-based permissions.

Every role check in this codebase used to be an ad-hoc `if request.user.role
not in (...)` inside a view, which is why some money-moving endpoints had no
check at all. Use these classes instead.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrManager(BasePermission):
    """Write access limited to owners and managers."""

    message = "Only an owner or manager can perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) in ("owner", "manager")
        )


class IsOwnerOrManagerOrReadOnly(BasePermission):
    """Anyone signed in may read; only owners and managers may write."""

    message = "Only an owner or manager can change this."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(user, "role", None) in ("owner", "manager")
