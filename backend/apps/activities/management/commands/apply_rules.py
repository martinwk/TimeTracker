"""
Management command om ActivityRules toe te passen op UniqueActivities.

Gebruik:
  python manage.py apply_rules                      # Verwerk alles
  python manage.py apply_rules --date 2026-03-13    # Één dag
  python manage.py apply_rules --from 2026-03-01 --to 2026-03-31  # Bereik
"""

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.activities.rule_engine import apply_rules


class Command(BaseCommand):
    help = "Voer ActivityRules toe op UniqueActivities, automatisch koppelen aan projecten."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Verwerk één dag (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--from",
            type=str,
            dest="date_from",
            help="Startdatum van bereik (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--to",
            type=str,
            dest="date_to",
            help="Einddatum van bereik (YYYY-MM-DD)",
        )

    def handle(self, *args, **options):
        date_str = options.get("date")
        date_from_str = options.get("date_from")
        date_to_str = options.get("date_to")

        # Parse dates
        date_from = None
        date_to = None

        if date_str:
            try:
                date_from = date_to = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as e:
                raise CommandError(f"Ongeldige datum: {date_str}. Gebruik YYYY-MM-DD.") from e

        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            except ValueError as e:
                raise CommandError(
                    f"Ongeldige startdatum: {date_from_str}. Gebruik YYYY-MM-DD."
                ) from e

        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
            except ValueError as e:
                raise CommandError(
                    f"Ongeldige einddatum: {date_to_str}. Gebruik YYYY-MM-DD."
                ) from e

        if date_from and date_to and date_from > date_to:
            raise CommandError("--from moet voor --to liggen")

        # Voer regels uit
        result = apply_rules(date_from=date_from, date_to=date_to)

        # Output
        date_range = (
            f"van {date_from} tot {date_to}"
            if date_from and date_to
            else f"op {date_from}" if date_from else "voor alle data"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ ActivityRules toegepast {date_range}\n"
                f"  {result.blocks_assigned} blokken toegewezen\n"
                f"  {result.blocks_skipped_manual} handmatig ingestelde overgeslagen\n"
                f"  {result.blocks_processed} blokken verwerkt"
            )
        )
