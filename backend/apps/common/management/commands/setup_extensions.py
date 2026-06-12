"""Create required PostgreSQL extensions.

Needed on managed Postgres (e.g. DO) where the docker init SQL does not run.
Run before `migrate`:  python manage.py setup_extensions
"""
from django.core.management.base import BaseCommand
from django.db import connection

EXTENSIONS = ["vector", "pg_trgm", "pgcrypto"]


class Command(BaseCommand):
    help = "CREATE EXTENSION IF NOT EXISTS for pgvector, pg_trgm, pgcrypto."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            for ext in EXTENSIONS:
                cursor.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext}";')
                self.stdout.write(self.style.SUCCESS(f"  extension ready: {ext}"))
