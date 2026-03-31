from datetime import date, datetime, timedelta, timezone

import pytest

from activities.aggregator import (
    DEFAULT_BLOCK_MINUTES,
    _build_blocks_for_day,
    _OpenBlock,
    aggregate_day,
)
from activities.models import ActivityBlock, WindowActivity


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_activity(title, start_offset_minutes, duration_seconds=30, app=None, save=False):
    """
    Maak een WindowActivity op 2026-03-13 startend op 09:00 + offset.
    app_name wordt automatisch geëxtraheerd uit title tenzij expliciet opgegeven.
    """
    base = datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc)
    started_at = base + timedelta(minutes=start_offset_minutes)
    ended_at   = started_at + timedelta(seconds=duration_seconds)
    a = WindowActivity.from_log_line(started_at, ended_at, title)
    if app:
        a.app_name = app
    if save:
        a.save()
    return a


# ── _OpenBlock ────────────────────────────────────────────────────────────────

def test_open_block_deadline():
    base = datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc)
    block = _OpenBlock(
        app_name="Firefox",
        started_at=base,
        ended_at=base,
        block_minutes=15,
    )
    assert block.deadline == base + timedelta(minutes=15)


def test_open_block_dominant_title():
    base = datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc)
    block = _OpenBlock(
        app_name="Firefox",
        started_at=base,
        ended_at=base,
        block_minutes=15,
    )
    a1 = make_activity("Pagina A - Firefox", 0, duration_seconds=10)
    a2 = make_activity("Pagina B - Firefox", 1, duration_seconds=50)
    a3 = make_activity("Pagina A - Firefox", 2, duration_seconds=5)
    block.add(a1)
    block.add(a2)
    block.add(a3)
    # Pagina B heeft 50 seconden, Pagina A heeft 15 seconden
    assert block.dominant_title == "Pagina B - Firefox"


# ── _build_blocks_for_day ─────────────────────────────────────────────────────

def test_single_activity_makes_one_block():
    activities = [make_activity("Zotero", 0, app="Zotero")]
    blocks = _build_blocks_for_day(activities, block_minutes=15)
    assert len(blocks) == 1
    assert blocks[0].app_name == "Zotero"
    assert blocks[0].activity_count == 1


def test_activities_within_window_merged():
    """Twee activiteiten binnen 15 minuten worden één blok."""
    activities = [
        make_activity("Zotero", 0,  app="Zotero"),
        make_activity("Zotero", 5,  app="Zotero"),
        make_activity("Zotero", 10, app="Zotero"),
    ]
    blocks = _build_blocks_for_day(activities, block_minutes=15)
    assert len(blocks) == 1
    assert blocks[0].activity_count == 3


def test_activities_outside_window_split():
    """Twee activiteiten meer dan 15 minuten uit elkaar worden twee blokken."""
    activities = [
        make_activity("Zotero", 0,  app="Zotero"),
        make_activity("Zotero", 20, app="Zotero"),
    ]
    blocks = _build_blocks_for_day(activities, block_minutes=15)
    assert len(blocks) == 2


def test_activity_exactly_at_deadline_opens_new_block():
    """Een activiteit precies op de deadline opent een nieuw blok."""
    activities = [
        make_activity("Zotero", 0,  app="Zotero"),
        make_activity("Zotero", 15, app="Zotero"),  # precies op deadline
    ]
    blocks = _build_blocks_for_day(activities, block_minutes=15)
    assert len(blocks) == 2


def test_total_seconds_summed():
    activities = [
        make_activity("Zotero", 0, duration_seconds=60, app="Zotero"),
        make_activity("Zotero", 5, duration_seconds=90, app="Zotero"),
    ]
    blocks = _build_blocks_for_day(activities, block_minutes=15)
    assert blocks[0].total_seconds == 150


def test_empty_activities_returns_no_blocks():
    assert _build_blocks_for_day([], block_minutes=15) == []


def test_custom_block_minutes():
    """Met een venster van 5 minuten worden dezelfde activiteiten gesplitst."""
    activities = [
        make_activity("Zotero", 0,  app="Zotero"),
        make_activity("Zotero", 10, app="Zotero"),
    ]
    blocks_15 = _build_blocks_for_day(activities, block_minutes=15)
    blocks_5  = _build_blocks_for_day(activities, block_minutes=5)
    assert len(blocks_15) == 1
    assert len(blocks_5)  == 2


# ── aggregate_day ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_aggregate_day_creates_blocks():
    make_activity("Zotero", 0,  app="Zotero", save=True)
    make_activity("Zotero", 5,  app="Zotero", save=True)
    make_activity("Firefox", 0, app="Firefox", save=True)

    result = aggregate_day(date(2026, 3, 13), block_minutes=15)

    assert result.blocks_created == 2       # één Zotero-blok, één Firefox-blok
    assert result.activities_processed == 3
    assert ActivityBlock.objects.count() == 2


@pytest.mark.django_db
def test_aggregate_day_excludes_noise():
    make_activity("Idle", 0, save=True)         # is_noise=True
    make_activity("Firefox", 5, app="Firefox", save=True)

    result = aggregate_day(date(2026, 3, 13), block_minutes=15)

    assert result.activities_processed == 1
    assert ActivityBlock.objects.count() == 1


@pytest.mark.django_db
def test_aggregate_day_deletes_existing_blocks():
    """Opnieuw aggregeren verwijdert eerst de oude blokken."""
    make_activity("Zotero", 0, app="Zotero", save=True)

    aggregate_day(date(2026, 3, 13), block_minutes=15)
    assert ActivityBlock.objects.count() == 1

    result = aggregate_day(date(2026, 3, 13), block_minutes=15)
    assert result.blocks_deleted == 1
    assert ActivityBlock.objects.count() == 1   # niet 2


@pytest.mark.django_db
def test_aggregate_day_reaggregate_with_different_window():
    """Opnieuw aggregeren met ander venster geeft andere blokindeling."""
    make_activity("Zotero", 0,  app="Zotero", save=True)
    make_activity("Zotero", 10, app="Zotero", save=True)

    aggregate_day(date(2026, 3, 13), block_minutes=15)
    assert ActivityBlock.objects.count() == 1   # samengevoegd

    aggregate_day(date(2026, 3, 13), block_minutes=5)
    assert ActivityBlock.objects.count() == 2   # gesplitst


@pytest.mark.django_db
def test_aggregate_day_no_activities_returns_zero():
    result = aggregate_day(date(2026, 3, 13), block_minutes=15)
    assert result.blocks_created == 0
    assert result.activities_processed == 0


@pytest.mark.django_db
def test_aggregate_day_block_has_correct_fields():
    make_activity("Koers zetten - Lockefeer - Zotero", 0, duration_seconds=120, app="Zotero", save=True)

    aggregate_day(date(2026, 3, 13), block_minutes=15)

    block = ActivityBlock.objects.get()
    assert block.app_name == "Zotero"
    assert block.total_seconds == 120
    assert block.activity_count == 1
    assert block.block_minutes == 15
    assert block.date == date(2026, 3, 13)
    assert block.dominant_title == "Koers zetten - Lockefeer - Zotero"


@pytest.mark.django_db
def test_aggregate_day_many_to_many_linked():
    """WindowActivity-records worden correct gekoppeld via UniqueActivity."""
    a1 = make_activity("Zotero", 0, app="Zotero", save=True)
    a2 = make_activity("Zotero", 5, app="Zotero", save=True)

    aggregate_day(date(2026, 3, 13), block_minutes=15)

    block = ActivityBlock.objects.get()
    # Get all WindowActivity instances linked to this block through unique_activities
    linked_ids = set(
        WindowActivity.objects
        .filter(unique_activity__block=block)
        .values_list("id", flat=True)
    )
    assert linked_ids == {a1.pk, a2.pk}
