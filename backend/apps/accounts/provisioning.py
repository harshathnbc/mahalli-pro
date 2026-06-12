"""
Master Admin (Tier 1) services — Concierge Onboarding, Soft-Hold, Ghost Login.

These operate ACROSS tenants (the Master Admin has no tenant) and therefore run via
the privileged DB path, outside the per-request RLS scoping.
"""
from __future__ import annotations

import secrets
import string

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import GhostLoginSession, Role, User
from apps.tenancy.models import (
    ComplianceYear,
    Subscription,
    Tenant,
    TenantBranch,
    TenantStatus,
)

_ALPHABET = string.ascii_letters + string.digits


def generate_temp_password(length: int = 14) -> str:
    """Cryptographically-strong temporary password for issued Super Admin creds."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


@transaction.atomic
def create_tenant_with_admin(
    *,
    name: str,
    cr_number: str,
    compliance_years: list[int],
    billing_email: str,
    billing_contact: str = "",
    billing_mobile: str = "",
    admin_email: str,
    max_employees: int = 0,
    max_vendors: int = 0,
    subscription_tier: str = "STARTER",
    branch_crs: list[str] | None = None,
) -> dict:
    """
    The 4-step provisioning wizard: company details (+ paid Compliance Years),
    billing contact, Super Admin creation, and tier quotas. Returns the new tenant
    and the generated Super Admin credentials (shown once).
    """
    tenant = Tenant.objects.create(
        name=name,
        primary_cr_number=cr_number,
        subscription_tier=subscription_tier,
        status=TenantStatus.ACTIVE,
        max_employees=max_employees,
        max_vendors=max_vendors,
    )

    # Main + branch CRs (Multi-CR Consolidation).
    TenantBranch.objects.create(tenant=tenant, cr_number=cr_number, is_main=True, label="Main")
    for cr in branch_crs or []:
        TenantBranch.objects.create(tenant=tenant, cr_number=cr, is_main=False)

    # Only the paid Compliance Years become selectable.
    for year in compliance_years:
        ComplianceYear.objects.create(tenant=tenant, year=year, is_paid=True)

    Subscription.objects.create(
        tenant=tenant,
        tier=subscription_tier,
        paid_years=sorted(set(compliance_years)),
        payment_status="FULLY_PAID",
    )

    temp_password = generate_temp_password()
    super_admin = User.objects.create_user(
        username=admin_email,
        email=admin_email,
        password=temp_password,
        tenant=tenant,
        role=Role.SUPER_ADMIN,
        mobile=billing_mobile,
    )

    return {
        "tenant_id": str(tenant.id),
        "super_admin_email": super_admin.email,
        "temp_password": temp_password,  # surfaced once to the Master Admin
        "paid_years": sorted(set(compliance_years)),
    }


def toggle_soft_hold(tenant: Tenant, *, hold: bool) -> Tenant:
    """
    The "Soft Hold": instantly lock out an entire tenant (all users logged out at the
    next request) while leaving their data untouched. Reversible.
    """
    tenant.hold_flag = hold
    tenant.status = TenantStatus.HOLD if hold else TenantStatus.ACTIVE
    tenant.save(update_fields=["hold_flag", "status"])
    return tenant


def start_ghost_login(*, master_admin: User, tenant: Tenant) -> dict:
    """
    "Log In As Tenant": issue a JWT for the tenant's Super Admin so the Master Admin
    sees the dashboard exactly as they do, and record the impersonation for audit.
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    target = User.objects.filter(tenant=tenant, role=Role.SUPER_ADMIN).first()
    if target is None:
        raise ValueError("Tenant has no Super Admin to impersonate.")

    session = GhostLoginSession.objects.create(master_admin=master_admin, target_tenant=tenant)
    refresh = RefreshToken.for_user(target)
    refresh["ghost"] = True
    refresh["ghost_session"] = str(session.id)
    return {
        "session_id": str(session.id),
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "impersonating": target.email,
    }


def end_ghost_login(session_id: str) -> None:
    GhostLoginSession.objects.filter(id=session_id, ended_at__isnull=True).update(
        ended_at=timezone.now()
    )
