"""Bootstrap demo + World Cup group-stage data on empty or demo-sized DBs (typical Render + Neon)."""

from __future__ import annotations

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

# Session-scoped lock id (arbitrary); avoids duplicate work if many Gunicorn workers start together.
_ADVISORY_LOCK_KEY = 872_341_010_01


class Command(BaseCommand):
    help = (
        "If there are no matches, run seed_demo. If World Cup rows are fewer than 72 and the "
        "existing WC count is small (demo-sized), run load_wc2026_fixtures --replace-wc. "
        "Set AUTO_LOAD_WC2026=0 to skip WC sync, or raise AUTO_LOAD_WC2026_MAX_EXISTING if you "
        "already curated more WC rows."
    )

    def handle(self, *args, **options):
        from matches.models import Match

        auto_wc = os.environ.get("AUTO_LOAD_WC2026", "1").lower() in ("1", "true", "yes")
        try:
            wc_max_existing = int(os.environ.get("AUTO_LOAD_WC2026_MAX_EXISTING", "8"))
        except ValueError:
            wc_max_existing = 8

        wc_count = Match.objects.filter(is_world_cup=True).count()
        need_seed = not Match.objects.exists()
        need_wc = auto_wc and wc_count < 72 and wc_count <= wc_max_existing

        if not need_seed and not need_wc:
            self.stdout.write("ensure_initial_data: skip (nothing to do).")
            return

        vendor = connection.vendor
        if vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_lock(%s)", [_ADVISORY_LOCK_KEY])
            try:
                self._run_locked(auto_wc, wc_max_existing)
            finally:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", [_ADVISORY_LOCK_KEY])
            return

        self._run_locked(auto_wc, wc_max_existing)

    def _run_locked(self, auto_wc: bool, wc_max_existing: int) -> None:
        from matches.models import Match

        if not Match.objects.exists():
            self.stdout.write("ensure_initial_data: loading demo teams/matches…")
            call_command("seed_demo")

        wc_count = Match.objects.filter(is_world_cup=True).count()
        need_wc = auto_wc and wc_count < 72 and wc_count <= wc_max_existing
        if need_wc:
            self.stdout.write(
                "ensure_initial_data: loading World Cup 2026 group stage (72 matches; replaces WC rows)…"
            )
            call_command("load_wc2026_fixtures", replace_wc=True)
        elif auto_wc and wc_count < 72:
            self.stdout.write(
                f"ensure_initial_data: skip WC auto-load ({wc_count} WC rows > "
                f"AUTO_LOAD_WC2026_MAX_EXISTING={wc_max_existing}). "
                "Run: python manage.py load_wc2026_fixtures --replace-wc"
            )
