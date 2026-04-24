"""
Management command: import_ahk_log

Gebruik:
    python manage.py import_ahk_log pad/naar/window_log.txt
    python manage.py import_ahk_log logs/week11.txt logs/week12.txt
    python manage.py import_ahk_log logs/*.txt
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.activities.importer import ImportResult, import_parsed_lines, parse_file


class Command(BaseCommand):
    help = "Importeer een of meerdere AHK-vensterlogbestanden in de database."

    def add_arguments(self, parser):
        parser.add_argument(
            "files",
            nargs="+",
            type=str,
            help="Pad(en) naar het/de te importeren logbestand(en).",
        )

    def handle(self, *args, **options):
        paths = [Path(f) for f in options["files"]]

        # Valideer eerst alle paden voordat we beginnen
        for path in paths:
            if not path.exists():
                raise CommandError(f"Bestand niet gevonden: {path}")
            if not path.is_file():
                raise CommandError(f"Geen geldig bestand: {path}")

        totaal = ImportResult(0, 0, 0, 0)

        for path in paths:
            self.stdout.write(f"Importeren: {path} ... ", ending="")
            self.stdout.flush()

            result = import_parsed_lines(parse_file(path))

            self.stdout.write(self.style.SUCCESS("klaar"))
            self.stdout.write(
                f"  {result.imported} nieuw  |  "
                f"{result.skipped_duplicates} duplicaten  |  "
                f"{result.skipped_parse_errors} fouten  |  "
                f"{result.total_lines} regels totaal"
            )

            totaal = ImportResult(
                total_lines=totaal.total_lines + result.total_lines,
                imported=totaal.imported + result.imported,
                skipped_duplicates=totaal.skipped_duplicates + result.skipped_duplicates,
                skipped_parse_errors=totaal.skipped_parse_errors + result.skipped_parse_errors,
            )

        if len(paths) > 1:
            self.stdout.write("─" * 50)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Totaal: {totaal.imported} nieuw  |  "
                    f"{totaal.skipped_duplicates} duplicaten  |  "
                    f"{totaal.skipped_parse_errors} fouten  |  "
                    f"{totaal.total_lines} regels"
                )
            )
