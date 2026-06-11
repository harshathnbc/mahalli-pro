"""
Immutable Data Lock guard (cross-module).

Once a ComplianceYear is LOCKED, HR / Procurement / Finance lose all
write/edit/delete privileges for that year's data, preventing post-certification
tampering. The Company Super Admin retains read-only access for downloads.

Usage in a viewset:

    from apps.tenancy.locking import YearLockWriteGuard
    permission_classes = [IsFinance, YearLockWriteGuard]

The guard inspects the target object's compliance year (or, on create, the
`compliance_year` in the request payload) and denies unsafe methods when LOCKED.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import Role
from apps.tenancy.models import ComplianceYear


def _year_is_locked(compliance_year_id, tenant_id) -> bool:
    if not compliance_year_id:
        return False
    return ComplianceYear.objects.filter(
        pk=compliance_year_id, tenant_id=tenant_id, state=ComplianceYear.State.LOCKED
    ).exists()


class YearLockWriteGuard(BasePermission):
    message = "This compliance year is LOCKED; its data is read-only post-certification."

    def has_permission(self, request, view):
        # Reads always allowed; only guard mutations at the collection level (create).
        if request.method in SAFE_METHODS:
            return True
        cy_id = request.data.get("compliance_year") if hasattr(request, "data") else None
        return not _year_is_locked(cy_id, getattr(request.user, "tenant_id", None))

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        cy = getattr(obj, "compliance_year_id", None)
        # Some rows reference the year indirectly (e.g. via upload).
        if cy is None:
            upload = getattr(obj, "upload", None)
            cy = getattr(upload, "compliance_year_id", None)
        return not _year_is_locked(cy, getattr(request.user, "tenant_id", None))


def assert_writable(compliance_year: ComplianceYear) -> None:
    """Service-layer guard for non-DRF write paths (e.g. Celery tasks)."""
    if compliance_year.state == ComplianceYear.State.LOCKED:
        raise PermissionError("Compliance year is LOCKED (Immutable Data Lock).")


def super_admin_read_only(user) -> bool:
    return user.role == Role.SUPER_ADMIN
