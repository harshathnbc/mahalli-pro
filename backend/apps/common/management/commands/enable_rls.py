"""Enable Row-Level Security policies on all tenant-scoped tables.

Run after `migrate` (deployment step 7):  python manage.py enable_rls
"""
from django.core.management.base import BaseCommand
from django.db import connection

from apps.common.rls import enable_rls_sql, tenant_scoped_tables


class Command(BaseCommand):
    help = "Enable PostgreSQL RLS tenant-isolation policies on all tenant-scoped tables."

    def handle(self, *args, **options):
        statements = enable_rls_sql()
        with connection.cursor() as cursor:
            for stmt in statements:
                cursor.execute(stmt)
        tables = tenant_scoped_tables()
        self.stdout.write(self.style.SUCCESS(f"RLS enabled on {len(tables)} tables:"))
        for table in tables:
            self.stdout.write(f"  • {table}")
