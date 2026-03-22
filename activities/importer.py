"""
Parser voor AHK-vensterlogbestanden.

Regelformaat:
    2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Venstertitel

De parser is bewust losgekoppeld van Django-modellen zodat hij
zowel door de management command als door de API-view gebruikt kan worden.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

ENCODING = "utf-8-sig"  # AHK schrijft vaak een BOM

# 2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Venstertitel
LINE_RE = re.compile(
    r"^(?P<start>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r" - "
    r"(?P<end>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r" \| \d+ min \| "
    r"(?P<title>.+)$"
)
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


@dataclass
class ParsedLine:
    started_at: datetime
    ended_at: datetime
    raw_title: str


@dataclass
class ImportResult:
    total_lines: int
    imported: int
    skipped_duplicates: int
    skipped_parse_errors: int


def parse_line(line: str) -> ParsedLine | None:
    """
    Parst één regel uit het logbestand.
    Geeft None terug als de regel niet matcht (lege regels, headers, etc.).
    """
    line = line.strip()
    if not line:
        return None
    match = LINE_RE.match(line)
    if not match:
        return None
    return ParsedLine(
        started_at=datetime.strptime(match.group("start"), DATETIME_FMT),
        ended_at=datetime.strptime(match.group("end"), DATETIME_FMT),
        raw_title=match.group("title").strip(),
    )


def parse_file(path: Path) -> Iterator[ParsedLine]:
    """
    Leest een logbestand en yield elke geldige ParsedLine.
    Sla ongeldige regels stilletjes over.
    """
    with path.open(encoding=ENCODING, errors="replace") as fh:
        for line in fh:
            parsed = parse_line(line)
            if parsed is not None:
                yield parsed


def parse_stream(stream) -> Iterator[ParsedLine]:
    """
    Zelfde als parse_file maar accepteert een bestandsachtig object
    (bv. een Django UploadedFile). Gebruikt door de API-view.
    """
    for raw_line in stream:
        if isinstance(raw_line, bytes):
            raw_line = raw_line.decode(ENCODING, errors="replace")
        parsed = parse_line(raw_line)
        if parsed is not None:
            yield parsed


import logging
from django.db import IntegrityError

logger = logging.getLogger(__name__)


def import_parsed_lines(lines: Iterator[ParsedLine]) -> ImportResult:
    from django.utils import timezone as django_tz
    from activities.models import WindowActivity

    imported = 0
    skipped_duplicates = 0
    skipped_parse_errors = 0
    total = 0

    for line in lines:
        total += 1
        try:
            started_at = django_tz.make_aware(line.started_at)
            ended_at   = django_tz.make_aware(line.ended_at)

            exists = WindowActivity.objects.filter(
                started_at=started_at,
                raw_title=line.raw_title,
            ).exists()

            if exists:
                skipped_duplicates += 1
                continue

            activity = WindowActivity.from_log_line(started_at, ended_at, line.raw_title)
            activity.save()
            imported += 1

        except ValueError as e:
            skipped_parse_errors += 1
            logger.warning(
                "Regel %d overgeslagen — ongeldige datum/tijd waarde '%s' in titel '%s': %s",
                total, line.started_at, line.raw_title, e,
            )

        except OverflowError as e:
            skipped_parse_errors += 1
            logger.warning(
                "Regel %d overgeslagen — tijdstempel buiten databasebereik '%s' in titel '%s': %s",
                total, line.started_at, line.raw_title, e,
            )

        except IntegrityError as e:
            skipped_parse_errors += 1
            logger.warning(
                "Regel %d overgeslagen — database constraint geschonden voor titel '%s' op '%s': %s",
                total, line.raw_title, line.started_at, e,
            )

    return ImportResult(
        total_lines=total,
        imported=imported,
        skipped_duplicates=skipped_duplicates,
        skipped_parse_errors=skipped_parse_errors,
    )
