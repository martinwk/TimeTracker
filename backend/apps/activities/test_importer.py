import io
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typing import Iterator

from apps.activities.importer import (
    ImportResult,
    ParsedLine,
    import_parsed_lines,
    parse_file,
    parse_line,
    parse_stream,
)

# ── parse_line ────────────────────────────────────────────────────────────────

def test_parse_line_valid():
    line = "2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Mozilla Firefox"
    result = parse_line(line)
    assert result is not None
    assert result.raw_title == "Mozilla Firefox"
    assert result.started_at == datetime(2026, 3, 13, 9, 14, 0)
    assert result.ended_at   == datetime(2026, 3, 13, 9, 14, 6)

def test_parse_line_with_em_dash_in_title():
    line = "2026-03-13 09:16:35 - 2026-03-13 09:16:48 | 000 min | Koers zetten richting digitale autonomie - Lockefeer - Zotero"
    result = parse_line(line)
    assert result is not None
    assert result.raw_title == "Koers zetten richting digitale autonomie - Lockefeer - Zotero"

def test_parse_line_empty():
    assert parse_line("") is None

def test_parse_line_whitespace_only():
    assert parse_line("   ") is None

def test_parse_line_invalid_format():
    assert parse_line("dit is geen logregel") is None

def test_parse_line_strips_title_whitespace():
    line = "2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min |   Notepad   "
    result = parse_line(line)
    assert result.raw_title == "Notepad"


# ── parse_file ────────────────────────────────────────────────────────────────

def test_parse_file(tmp_path):
    log = tmp_path / "test.txt"
    log.write_text(
        "2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Mozilla Firefox\n"
        "dit is geen geldige regel\n"
        "2026-03-13 09:14:06 - 2026-03-13 09:14:09 | 000 min | Visual Studio Code\n",
        encoding="utf-8",
    )
    results = list(parse_file(log))
    assert len(results) == 2
    assert results[0].raw_title == "Mozilla Firefox"
    assert results[1].raw_title == "Visual Studio Code"

def test_parse_file_skips_empty_lines(tmp_path):
    log = tmp_path / "test.txt"
    log.write_text(
        "\n"
        "2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Notepad\n"
        "\n",
        encoding="utf-8",
    )
    results = list(parse_file(log))
    assert len(results) == 1


# ── parse_stream ──────────────────────────────────────────────────────────────

def test_parse_stream_text():
    content = (
        "2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Mozilla Firefox\n"
        "2026-03-13 09:14:06 - 2026-03-13 09:14:09 | 000 min | Idle\n"
    )
    stream = io.StringIO(content)
    results = list(parse_stream(stream))
    assert len(results) == 2

def test_parse_stream_bytes():
    content = b"2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Mozilla Firefox\n"
    stream = io.BytesIO(content)
    results = list(parse_stream(stream))
    assert len(results) == 1
    assert results[0].raw_title == "Mozilla Firefox"


# ── import_parsed_lines ───────────────────────────────────────────────────────

def make_line(title="Mozilla Firefox", offset_seconds=0):
    from datetime import timedelta
    base = datetime(2026, 3, 13, 9, 0)  # naïef, zoals de parser ze aanmaakt
    start = base + timedelta(seconds=offset_seconds)
    end   = start + timedelta(seconds=10)
    return ParsedLine(started_at=start, ended_at=end, raw_title=title)


@pytest.mark.django_db
def test_import_creates_activities():
    lines = [make_line("Firefox", 0), make_line("Zotero", 10)]
    result = import_parsed_lines(iter(lines))
    assert result.imported == 2
    assert result.skipped_duplicates == 0
    assert result.total_lines == 2


@pytest.mark.django_db
def test_import_skips_duplicates():
    line = make_line("Firefox", 0)
    import_parsed_lines(iter([line]))
    result = import_parsed_lines(iter([line]))  # zelfde regel opnieuw
    assert result.imported == 0
    assert result.skipped_duplicates == 1


@pytest.mark.django_db
def test_import_marks_noise():
    from apps.activities.models import WindowActivity
    lines = [make_line("Idle", 0), make_line("Firefox", 10)]
    import_parsed_lines(iter(lines))
    assert WindowActivity.objects.filter(is_noise=True).count() == 1
    assert WindowActivity.objects.filter(is_noise=False).count() == 1


@pytest.mark.django_db
def test_import_real_file(tmp_path):
    log = tmp_path / "window_log.txt"
    log.write_text(
        "2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Mozilla Firefox\n"
        "2026-03-13 09:14:06 - 2026-03-13 09:14:09 | 000 min | Program Manager\n"
        "2026-03-13 09:14:09 - 2026-03-13 09:15:00 | 000 min | track_window_log.ahk - AutoHotkey - Visual Studio Code\n",
        encoding="utf-8",
    )
    result = import_parsed_lines(parse_file(log))
    assert result.imported == 3
    assert result.total_lines == 3

def import_parsed_lines(lines: Iterator[ParsedLine]) -> ImportResult:
    """
    Sla ParsedLines op in de database.
    Duplicaten (zelfde started_at + raw_title) worden overgeslagen.
    Geeft een ImportResult terug met tellingen.
    """
    from django.utils import timezone as django_tz

    from apps.activities.models import WindowActivity

    imported = 0
    skipped_duplicates = 0
    skipped_parse_errors = 0
    total = 0

    for line in lines:
        total += 1
        try:
            # Maak tijdzone-aware (gebruik de tijdzone uit settings)
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

        except Exception:
            skipped_parse_errors += 1

    return ImportResult(
        total_lines=total,
        imported=imported,
        skipped_duplicates=skipped_duplicates,
        skipped_parse_errors=skipped_parse_errors,
    )

@pytest.mark.django_db
def test_reimport_same_file_no_duplicates(tmp_path):
    """Hetzelfde bestand twee keer importeren geeft geen dubbele records."""
    from apps.activities.models import WindowActivity

    log = tmp_path / "window_log.txt"
    log.write_text(
        "2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Mozilla Firefox\n"
        "2026-03-13 09:14:06 - 2026-03-13 09:14:09 | 000 min | Visual Studio Code\n"
        "2026-03-13 09:14:09 - 2026-03-13 09:14:12 | 000 min | Idle\n",
        encoding="utf-8",
    )

    first  = import_parsed_lines(parse_file(log))
    second = import_parsed_lines(parse_file(log))

    assert first.imported == 3
    assert second.imported == 0
    assert second.skipped_duplicates == 3
    assert WindowActivity.objects.count() == 3  # geen dubbelen in de database


@pytest.mark.django_db
def test_reimport_partial_overlap(tmp_path):
    """Bestand met deels nieuwe, deels bekende regels."""
    from apps.activities.models import WindowActivity

    log_week11 = tmp_path / "week11.txt"
    log_week11.write_text(
        "2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | Mozilla Firefox\n"
        "2026-03-13 09:14:06 - 2026-03-13 09:14:09 | 000 min | Visual Studio Code\n",
        encoding="utf-8",
    )

    # Week 12 bevat de laatste regel van week 11 + nieuwe regels
    log_week12 = tmp_path / "week12.txt"
    log_week12.write_text(
        "2026-03-13 09:14:06 - 2026-03-13 09:14:09 | 000 min | Visual Studio Code\n"
        "2026-03-14 08:00:00 - 2026-03-14 08:30:00 | 030 min | Outlook\n",
        encoding="utf-8",
    )

    import_parsed_lines(parse_file(log_week11))
    result = import_parsed_lines(parse_file(log_week12))

    assert result.imported == 1
    assert result.skipped_duplicates == 1
    assert WindowActivity.objects.count() == 3


@pytest.mark.django_db
def test_reimport_same_title_different_time_is_not_duplicate(tmp_path):
    """Zelfde venstertitel op een ander tijdstip is geen duplicaat."""
    from apps.activities.models import WindowActivity

    log = tmp_path / "window_log.txt"
    log.write_text(
        "2026-03-13 09:00:00 - 2026-03-13 09:01:00 | 001 min | Mozilla Firefox\n"
        "2026-03-13 10:00:00 - 2026-03-13 10:01:00 | 001 min | Mozilla Firefox\n",
        encoding="utf-8",
    )

    result = import_parsed_lines(parse_file(log))

    assert result.imported == 2
    assert result.skipped_duplicates == 0
    assert WindowActivity.objects.count() == 2