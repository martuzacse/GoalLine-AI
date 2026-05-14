"""Load demo fixtures when the DB has no matches (typical fresh Neon + Render deploy)."""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

# Session-scoped lock id (arbitrary); avoids duplicate seed_demo if many Gunicorn workers start together.
_ADVISORY_LOCK_KEY = 872_341_010_01


class Command(BaseCommand):
    help = "If there are no matches, run seed_demo (Postgres: advisory lock so only one worker seeds)."

    def handle(self, *args, **options):
        from matches.models import Match

        if Match.objects.exists():
            self.stdout.write("ensure_initial_data: skip (matches already exist).")
            return

        vendor = connection.vendor
        if vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_lock(%s)", [_ADVISORY_LOCK_KEY])
            try:
                if Match.objects.exists():
                    self.stdout.write("ensure_initial_data: skip (seeded by another worker).")
                    return
                self.stdout.write("ensure_initial_data: loading demo teams/matches…")
                call_command("seed_demo")
            finally:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", [_ADVISORY_LOCK_KEY])
            return

        self.stdout.write("ensure_initial_data: loading demo teams/matches…")
        call_command("seed_demo")
