"""Install a DB trigger that makes the audit log append-only (rejects UPDATE/DELETE).

Run after `migrate` (deployment step 7):  python manage.py install_audit_guard
"""
from django.core.management.base import BaseCommand
from django.db import connection

from apps.audit.models import AuditLog

SQL = """
CREATE OR REPLACE FUNCTION mahalli_block_audit_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Audit log is append-only; % is not permitted', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_append_only ON "{table}";
CREATE TRIGGER trg_audit_append_only
    BEFORE UPDATE OR DELETE ON "{table}"
    FOR EACH ROW EXECUTE FUNCTION mahalli_block_audit_mutation();
"""


class Command(BaseCommand):
    help = "Install the append-only immutability trigger on the audit log table."

    def handle(self, *args, **options):
        table = AuditLog._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(SQL.format(table=table))
        self.stdout.write(self.style.SUCCESS(f"Append-only trigger installed on {table}."))
