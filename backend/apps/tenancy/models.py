"""
Module 1 — SaaS Administration & Company Profiling (tenancy half).

Tenant provisioning, Multi-CR consolidation, compliance years (with the Immutable
Data Lock), company profile validation, and the Contract/Tender dimension required
by the official Entity-Level and Contract-Level LCGPA templates.
"""
from django.db import models

from apps.common.models import BaseModel, TenantScopedModel
from apps.common.validators import (
    cr_number_validator,
    wasel_validator,
    zatca_vat_validator,
)


class SubscriptionTier(models.TextChoices):
    STARTER = "STARTER", "Starter"
    GROWTH = "GROWTH", "Growth"
    ENTERPRISE = "ENTERPRISE", "Enterprise"


class TenantStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    HOLD = "HOLD", "Hold (billing suspended)"


class BillingStatus(models.TextChoices):
    FULLY_PAID = "FULLY_PAID", "Fully Paid"
    PARTIAL_PAID = "PARTIAL_PAID", "Partial Paid"
    DELAYED = "DELAYED", "Delayed"


class Tenant(BaseModel):
    """A company using Mahalli Pro. Provisioned by the Master Admin wizard."""

    name = models.CharField(max_length=255)
    primary_cr_number = models.CharField(max_length=10, validators=[cr_number_validator])
    subscription_tier = models.CharField(
        max_length=20, choices=SubscriptionTier.choices, default=SubscriptionTier.STARTER
    )
    status = models.CharField(
        max_length=10, choices=TenantStatus.choices, default=TenantStatus.ACTIVE
    )
    billing_status = models.CharField(
        max_length=15, choices=BillingStatus.choices, default=BillingStatus.FULLY_PAID
    )
    # Tier quotas set during provisioning.
    max_employees = models.PositiveIntegerField(default=0)
    max_vendors = models.PositiveIntegerField(default=0)
    # Billing & Access Control: the "Soft Hold" instantly locks out the tenant.
    hold_flag = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class TenantBranch(TenantScopedModel):
    """Multi-CR Consolidation Engine — main CR + branch CRs merged for calculations."""

    cr_number = models.CharField(max_length=10, validators=[cr_number_validator])
    is_main = models.BooleanField(default=False)
    label = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "cr_number"], name="uq_branch_cr_per_tenant"),
        ]


class ComplianceYear(TenantScopedModel):
    """A paid working year. Becomes LOCKED (immutable) after the Annual Hard-Close."""

    class State(models.TextChoices):
        OPEN = "OPEN", "Open"
        LOCKED = "LOCKED", "Locked (post-certification)"

    year = models.PositiveSmallIntegerField()
    is_paid = models.BooleanField(default=True)
    state = models.CharField(max_length=10, choices=State.choices, default=State.OPEN)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "year"], name="uq_year_per_tenant"),
        ]

    def __str__(self):
        return f"{self.tenant_id}:{self.year}"


class CompanyProfile(TenantScopedModel):
    """Company-level profile with strict LCGPA / ZATCA / Wasel validation."""

    cr_number = models.CharField(max_length=10, validators=[cr_number_validator])
    zatca_vat = models.CharField(max_length=15, validators=[zatca_vat_validator])
    national_address_wasel = models.CharField(max_length=8, validators=[wasel_validator])
    isic_sector = models.ForeignKey(
        "seed.IsicSector", on_delete=models.PROTECT, related_name="company_profiles"
    )
    consolidates_multi_cr = models.BooleanField(default=False)


class Contract(TenantScopedModel):
    """
    A government tender/contract. Enables Contract-Level reporting required by the
    official Target / Periodic / Final templates (Entity-Level uses contract=null).
    """

    compliance_year = models.ForeignKey(
        ComplianceYear, on_delete=models.CASCADE, related_name="contracts"
    )
    tender_name = models.CharField(max_length=255)
    gov_entity = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    cr_scope = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.tender_name


class Subscription(TenantScopedModel):
    """Billing record. Paid compliance years gate what the Super Admin may select."""

    tier = models.CharField(max_length=20, choices=SubscriptionTier.choices)
    paid_years = models.JSONField(default=list)  # e.g. [2025, 2026]
    payment_status = models.CharField(max_length=15, choices=BillingStatus.choices)
    hold_flag = models.BooleanField(default=False)
