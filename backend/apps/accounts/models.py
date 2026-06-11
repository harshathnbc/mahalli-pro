"""
Module 1 — Identity, the 3-Tier Hierarchy, RBAC, and Ghost Login.

Tier 1 Master Admin (no tenant) · Tier 2 Company Super Admin · Tier 3 Department
Admins. RBAC roles form the "cryptographic wall": cross-department visibility is
prohibited (enforced in DRF permissions; RLS isolates across tenants).
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    MASTER_ADMIN = "MASTER_ADMIN", "Master Admin (system)"
    SUPER_ADMIN = "SUPER_ADMIN", "Company Super Admin"
    COMPANY_ADMIN = "COMPANY_ADMIN", "Company Admin (Setup/Export)"
    HR_ADMIN = "HR_ADMIN", "HR Admin (Section 3/6)"
    PROCUREMENT_ADMIN = "PROCUREMENT_ADMIN", "Procurement Admin (Section 4)"
    FINANCE_ADMIN = "FINANCE_ADMIN", "Finance Admin (Appendix A / Section 7)"


# Which LCGPA sections each role may access (the department silo map).
ROLE_SECTION_ACCESS = {
    Role.HR_ADMIN: {"3", "6"},
    Role.PROCUREMENT_ADMIN: {"4"},
    Role.FINANCE_ADMIN: {"A", "7"},
    Role.COMPANY_ADMIN: {"setup", "export"},
}


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Master Admin has tenant=null; everyone else belongs to exactly one tenant.
    tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True, on_delete=models.CASCADE, related_name="users"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.COMPANY_ADMIN)
    mobile = models.CharField(max_length=20, blank=True)

    @property
    def is_master_admin(self) -> bool:
        return self.role == Role.MASTER_ADMIN

    def can_access_section(self, section: str) -> bool:
        if self.role in (Role.MASTER_ADMIN, Role.SUPER_ADMIN):
            return True
        return section in ROLE_SECTION_ACCESS.get(self.role, set())


class GhostLoginSession(models.Model):
    """Audit record for Master Admin support impersonation ("Log In As Tenant")."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    master_admin = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ghost_sessions"
    )
    target_tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
