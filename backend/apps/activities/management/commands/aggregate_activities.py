"""
Management command: aggregate_activities

Gebruik:
    # Aggregeer vandaag (standaard 15 minuten venster)
    python manage.py aggregate_activities

    # Specifieke datum
    python manage.py aggregate_activities --date 2026-03-13

    # Datumbereik
    python manage.py aggregate_activities --from 2026-03-01 --to 2026-03-31

    # Aangepast tijdvenster
    python manage.py aggregate_activities --block-minutes 30

    # Alles opnieuw aggregeren vanuit de database
    python manage.py aggregate_activities --all
"""

from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from apps.activities.aggregator import DEFAULT_BLOCK_MINUTES, aggregate_day, aggregate_range
from apps.activities.models import WindowActivity


class Command(BaseCommand):
    help = "Aggregeer WindowActivity-regels tot ActivityBlocks."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--date",
            type=str,
            metavar="YYYY-MM-DD",
            help="Aggregeer één specifieke datum.",
        )
        group.add_argument(
            "--all",
            action="store_true",
            help="Aggregeer alle datums die aanwezig zijn in de database.",
        )

        parser.add_argument(
            "--from",
            dest="date_from",
            type=str,
            metavar="YYYY-MM-DD",
            help="Begindatum van een bereik (gebruik samen met --to).",
        )
        parser.add_argument(
            "--to",
            dest="date_to",
            type=str,
            metavar="YYYY-MM-DD",
            help="Einddatum van een bereik (gebruik samen met --from).",
        )
        parser.add_argument(
            "--block-minutes",
            type=int,
            default=DEFAULT_BLOCK_MINUTES,
            metavar="N",
            help=f"Tijdvenster in minuten (standaard: {DEFAULT_BLOCK_MINUTES}).",
        )

    def handle(self, *args, **options):
        block_minutes = options["block_minutes"]
        if block_minutes < 1:
            raise CommandError("--block-minutes moet minimaal 1 zijn.")

        # Bepaal welke datums we aggregeren
        dates = self._resolve_dates(options)

        if not dates:
            self.stdout.write(self.style.WARNING("Geen activiteiten gevonden om te aggregeren."))
            return

        self.stdout.write(
            f"Aggregeren van {len(dates)} dag(en) met venster van {block_minutes} minuten...\n"
        )

        totaal_blokken = 0
        totaal_activiteiten = 0

        for target_date in sorted(dates):
            result = aggregate_day(target_date, block_minutes)
            totaal_blokken += result.blocks_created
            totaal_activiteiten += result.activities_processed

            self.stdout.write(
                f"  {target_date}  →  "
                f"{result.blocks_created:3d} blokken  |  "
                f"{result.activities_processed:4d} activiteiten"
                + (f"  |  {result.blocks_deleted} oud verwijderd" if result.blocks_deleted else "")
            )

        self.stdout.write("─" * 55)
        self.stdout.write(
            self.style.SUCCESS(
                f"Klaar: {totaal_blokken} blokken aangemaakt uit {totaal_activiteiten} activiteiten."
            )
        )

    def _resolve_dates(self, options) -> list[date]:
        """Vertaal de CLI-opties naar een lijst van te aggregeren datums."""

        if options.get("date"):
            return [self._parse_date(options["date"])]

        if options.get("all"):
            return list(
                WindowActivity.objects
                .filter(is_noise=False)
                .dates("date", "day")
            )

        if options.get("date_from") or options.get("date_to"):
            if not (options.get("date_from") and options.get("date_to")):
                raise CommandError("Gebruik --from en --to samen.")
            date_from = self._parse_date(options["date_from"])
            date_to   = self._parse_date(options["date_to"])
            if date_from > date_to:
                raise CommandError("--from moet vóór --to liggen.")
            # Alleen datums met data
            return list(
                WindowActivity.objects
                .filter(date__range=(date_from, date_to), is_noise=False)
                .dates("date", "day")
            )

        # Standaard: vandaag
        return [date.today()]

    @staticmethod
    def _parse_date(value: str) -> date:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise CommandError(f"Ongeldige datum '{value}'. Gebruik YYYY-MM-DD.")
