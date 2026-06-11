"""
Helpers to enable PostgreSQL Row-Level Security on every tenant-scoped table.

A table is tenant-scoped iff its model subclasses TenantScopedModel (i.e. has a
`tenant_id` column). For each such table we enable RLS and install a policy that
restricts all rows to the current session tenant.
"""
from django.apps import apps as django_apps

from apps.common.models import TenantScopedModel

POLICY_NAME = "tenant_isolation"


def tenant_scoped_tables() -> list[str]:
    tables = []
    for model in django_apps.get_models():
        if issubclass(model, TenantScopedModel) and not model._meta.abstract:
            tables.append(model._meta.db_table)
    return sorted(set(tables))


def enable_rls_sql() -> list[str]:
    stmts: list[str] = []
    for table in tenant_scoped_tables():
        stmts.append(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')
        stmts.append(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;')
        stmts.append(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}";')
        stmts.append(
            f'CREATE POLICY {POLICY_NAME} ON "{table}" '
            "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid) "
            "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);"
        )
    return stmts
