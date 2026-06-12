"""
RBAC permissions — the department "cryptographic wall".

Each department viewset declares the role(s) allowed to touch it. Super Admin and
Company Admin have cross-department reach; HR/Procurement/Finance are siloed to
their own sections. RLS still isolates tenants beneath this layer.
"""
from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


class IsMasterAdmin(BasePermission):
    """Tier 1 — platform owner only (no tenant). Operates across all tenants."""

    message = "Master Admin access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.MASTER_ADMIN)


class HasRole(BasePermission):
    """Grant access if the user's role is in the view's `allowed_roles` set.

    Super Admin is always allowed within their tenant.
    """

    message = "Your role does not have access to this department."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        allowed = set(getattr(view, "allowed_roles", set())) | {Role.SUPER_ADMIN}
        return user.role in allowed


class IsProcurement(HasRole):
    """Convenience for Section 4 endpoints (Procurement Admin + Super/Company Admin)."""

    def has_permission(self, request, view):
        view.allowed_roles = {Role.PROCUREMENT_ADMIN, Role.COMPANY_ADMIN}
        return super().has_permission(request, view)


class IsHR(HasRole):
    """Section 3/6 endpoints (HR Admin + Super/Company Admin)."""

    def has_permission(self, request, view):
        view.allowed_roles = {Role.HR_ADMIN, Role.COMPANY_ADMIN}
        return super().has_permission(request, view)


class IsFinance(HasRole):
    """Appendix A / Section 7 endpoints (Finance Admin + Super/Company Admin)."""

    def has_permission(self, request, view):
        view.allowed_roles = {Role.FINANCE_ADMIN, Role.COMPANY_ADMIN}
        return super().has_permission(request, view)


class IsExport(HasRole):
    """Setup/Export endpoints — Company Admin (Setup/Export) + Super Admin."""

    def has_permission(self, request, view):
        view.allowed_roles = {Role.COMPANY_ADMIN}
        return super().has_permission(request, view)
