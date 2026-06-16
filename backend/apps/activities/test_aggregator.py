"""
Tests voor de vaste-raster aggregator.

Ontwerp: de dag wordt verdeeld in vaste 15-minutenslots.
Per slot worden alle WindowActivity-records die overlap hebben met
dat slot gecombineerd. Daardoor zijn overlappende ActivityBlocks
structureel onmogelijk.
"""

from datetime import date, datetime, timedelta

import pytest
from django.utils.timezone import make_aware

from apps.activities.aggregator import DEFAULT_BLOCK_MINUTES, aggregate_day
from apps.activities.models import ActivityBlock, UniqueActivity, WindowActivity


# ── Helpers ───────────────────────────────────────────────────────────────────

TARGET_DATE = date(2026, 3, 13)


def local_dt(hour, minute=0, second=0):
    """Timezone-aware datetime op TARGET_DATE in de geconfigureerde tijdzone."""
    return make_aware(datetime(TARGET_DATE.year, TARGET_DATE.month, TARGET_DATE.day,
                               hour, minute, second))


def make_activity(title, start_hour, start_minute=0, duration_seconds=30,
                  app=None, save=False):
    """WindowActivity op TARGET_DATE."""
    started_at = local_dt(start_hour, start_minute)
    ended_at   = started_at + timedelta(seconds=duration_seconds)
    a = WindowActivity.from_log_line(started_at, ended_at, title)
    if app:
        a.app_name = app
    if save:
        a.save()
    return a


def slot_start(hour, minute=0):
    """Verwachte started_at van een 15-minutenslot."""
    return local_dt(hour, minute)


def slot_end(hour, minute=0):
    """Verwachte ended_at van een 15-minutenslot."""
    return local_dt(hour, minute) + timedelta(minutes=DEFAULT_BLOCK_MINUTES)


# ── Basisgedrag ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_empty_day_creates_no_blocks():
    result = aggregate_day(TARGET_DATE)
    assert result.blocks_created == 0
    assert ActivityBlock.objects.count() == 0


@pytest.mark.django_db
def test_single_activity_creates_one_block():
    make_activity("VS Code", 9, 0, duration_seconds=60, save=True)

    result = aggregate_day(TARGET_DATE)

    assert result.blocks_created == 1
    assert ActivityBlock.objects.count() == 1


@pytest.mark.django_db
def test_block_is_aligned_to_15min_grid():
    """Blok begint altijd op een veelvoud van 15 minuten."""
    make_activity("VS Code", 9, 7, duration_seconds=60, save=True)  # 09:07

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.get()
    assert block.started_at == slot_start(9, 0)


@pytest.mark.django_db
def test_block_spans_exactly_15_minutes():
    """ended_at is altijd started_at + 15 min."""
    make_activity("VS Code", 9, 0, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.get()
    assert block.ended_at == block.started_at + timedelta(minutes=DEFAULT_BLOCK_MINUTES)


@pytest.mark.django_db
def test_activity_spanning_two_slots_creates_two_blocks():
    """Activiteit van 09:05–09:20 → slot 09:00 én slot 09:15."""
    make_activity("VS Code", 9, 5, duration_seconds=15 * 60, save=True)  # 15 minuten

    aggregate_day(TARGET_DATE)

    assert ActivityBlock.objects.count() == 2
    starts = sorted(ActivityBlock.objects.values_list("started_at", flat=True))
    assert starts[0] == slot_start(9, 0)
    assert starts[1] == slot_start(9, 15)


@pytest.mark.django_db
def test_two_activities_same_slot_creates_one_block():
    """Twee activiteiten in hetzelfde slot → één blok."""
    make_activity("VS Code", 9, 2, duration_seconds=60, save=True)
    make_activity("VS Code", 9, 8, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    assert ActivityBlock.objects.count() == 1


@pytest.mark.django_db
def test_two_activities_different_slots_create_two_blocks():
    """Activiteiten in aparte slots → twee blokken."""
    make_activity("VS Code", 9,  0, duration_seconds=60, save=True)
    make_activity("VS Code", 9, 20, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    assert ActivityBlock.objects.count() == 2


# ── Dominant title ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_dominant_title_is_activity_with_most_overlap():
    """Titel met meeste overlap-seconden in het slot wint."""
    # A: 2 sec overlap, B: 10 sec overlap → dominant = B
    make_activity("Pagina A - Firefox", 9, 0, duration_seconds=2, save=True)
    make_activity("Pagina B - Firefox", 9, 2, duration_seconds=10, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.get()
    assert block.dominant_title == "Pagina B - Firefox"


@pytest.mark.django_db
def test_dominant_title_uses_overlap_not_total_duration():
    """
    Activiteit A loopt van 09:00–09:20 (20 min), maar heeft slechts 15 sec
    overlap met slot 09:00–09:15.
    Activiteit B loopt van 09:05–09:10 (5 min) en heeft 5 min overlap.
    B wint voor dit slot (5 min > truncated portion of A in this slot).
    """
    # A: start 09:00, 20 min → overlap met 09:00-slot = 15 min = 900 sec
    make_activity("Lang - App", 9, 0, duration_seconds=20 * 60, save=True)
    # B: start 09:05, 5 min → overlap = 5 min = 300 sec
    make_activity("Kort - App", 9, 5, duration_seconds=5 * 60, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.filter(started_at=slot_start(9, 0)).get()
    # Lang heeft 900 sec overlap, Kort heeft 300 sec → Lang wint
    assert "Lang" in block.dominant_title


# ── total_seconds ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_total_seconds_is_overlap_in_slot():
    """total_seconds = overlap-seconden in het slot, niet de volle activiteitsduur."""
    # Activiteit van 09:10–09:25 → overlap met slot 09:00-09:15 = 5 min = 300 sec
    make_activity("VS Code", 9, 10, duration_seconds=15 * 60, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.filter(started_at=slot_start(9, 0)).get()
    assert block.total_seconds == 5 * 60  # alleen de 5 minuten in dit slot


@pytest.mark.django_db
def test_total_seconds_full_slot_when_activity_covers_entirely():
    """Activiteit die het hele slot dekt → total_seconds = block_minutes * 60."""
    make_activity("VS Code", 9, 0, duration_seconds=20 * 60, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.filter(started_at=slot_start(9, 0)).get()
    assert block.total_seconds == DEFAULT_BLOCK_MINUTES * 60


# ── Ruis ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_noise_activities_excluded():
    make_activity("Idle", 9, 0, duration_seconds=60, save=True)       # is_noise=True
    make_activity("VS Code", 9, 5, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    assert ActivityBlock.objects.count() == 1


# ── Geen overlapping ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_no_overlapping_blocks():
    """Structurele garantie: geen enkel paar blokken overlapt."""
    for minute in range(0, 60, 3):
        make_activity(f"App {minute} - Programma", 9, minute,
                      duration_seconds=5 * 60, save=True)

    aggregate_day(TARGET_DATE)

    blocks = list(ActivityBlock.objects.order_by("started_at"))
    pairs  = list(zip(blocks, blocks[1:]))
    assert all(a.ended_at <= b.started_at for a, b in pairs), (
        "Overlappende blokken gevonden: "
        + ", ".join(f"{a.started_at}↔{b.started_at}" for a, b in pairs
                    if a.ended_at > b.started_at)
    )


# ── Heraggregatie ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_reaggregation_replaces_old_blocks():
    make_activity("VS Code", 9, 0, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)
    assert ActivityBlock.objects.count() == 1

    result = aggregate_day(TARGET_DATE)
    assert result.blocks_deleted == 1
    assert ActivityBlock.objects.count() == 1  # niet 2


# ── Veldwaarden ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_block_fields_are_correct():
    make_activity("Koers zetten - Lockefeer - Zotero", 9, 0,
                  duration_seconds=120, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.get()
    assert block.app_name == "Zotero"
    assert block.date == TARGET_DATE
    assert block.block_minutes == DEFAULT_BLOCK_MINUTES
    assert block.started_at == slot_start(9, 0)
    assert block.ended_at   == slot_end(9, 0)


# ── UniqueActivity ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_unique_activity_created_per_title():
    make_activity("Pagina A - Firefox", 9, 0, duration_seconds=30, save=True)
    make_activity("Pagina B - Firefox", 9, 5, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.get()
    assert UniqueActivity.objects.filter(block=block).count() == 2


@pytest.mark.django_db
def test_unique_activity_seconds_reflect_overlap():
    """UniqueActivity.total_seconds = overlap van die titel met het slot."""
    # Activiteit B heeft 300 sec overlap in het slot
    make_activity("Pagina B - Firefox", 9, 5, duration_seconds=5 * 60, save=True)

    aggregate_day(TARGET_DATE)

    ua = UniqueActivity.objects.get()
    assert ua.total_seconds == 5 * 60


@pytest.mark.django_db
def test_unique_activity_seconds_per_slot_when_crossing_boundary():
    """
    Activiteit 12:29–12:34 overschrijdt de 12:30-grens.
    Slot 12:15–12:30: overlap = 1 min = 60 sec.
    Slot 12:30–12:45: overlap = 4 min = 240 sec.
    UniqueActivity.total_seconds moet per slot de OVERLAP bevatten,
    niet de volle activiteitsduur.
    """
    make_activity("Inbox - Firefox", 12, 29, duration_seconds=5 * 60, save=True)

    aggregate_day(TARGET_DATE)

    block_1215 = ActivityBlock.objects.get(started_at=slot_start(12, 15))
    block_1230 = ActivityBlock.objects.get(started_at=slot_start(12, 30))

    ua_1215 = UniqueActivity.objects.get(block=block_1215)
    ua_1230 = UniqueActivity.objects.get(block=block_1230)

    assert ua_1215.total_seconds == 60,  f"slot 12:15 verwacht 60 sec, kreeg {ua_1215.total_seconds}"
    assert ua_1230.total_seconds == 240, f"slot 12:30 verwacht 240 sec, kreeg {ua_1230.total_seconds}"


@pytest.mark.django_db
def test_window_activity_linked_to_unique_activity():
    a = make_activity("VS Code", 9, 0, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    a.refresh_from_db()
    assert a.unique_activity is not None
    assert a.unique_activity.block is not None


# ── Optie C: handmatige toewijzingen overleven herberekening ──────────────────

@pytest.mark.django_db
def test_reaggregate_restores_manual_assignment():
    """Handmatig toegewezen blokken krijgen na herberekening hun project terug."""
    from apps.projects.models import Project
    from apps.activities.models import BlockProjectHistory

    project = Project.objects.create(name="Alpha", color="#aabbcc")
    make_activity("VS Code", 9, 0, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.get(date=TARGET_DATE)
    block.project = project
    block.save()
    BlockProjectHistory.objects.create(block=block, project=project, assigned_by="manual")

    # Herberekening
    aggregate_day(TARGET_DATE)

    new_block = ActivityBlock.objects.get(date=TARGET_DATE, started_at=slot_start(9, 0))
    assert new_block.project == project


@pytest.mark.django_db
def test_reaggregate_creates_history_for_restored_assignment():
    """Na herberekening staat de herstelde handmatige toewijzing in BlockProjectHistory."""
    from apps.projects.models import Project
    from apps.activities.models import BlockProjectHistory

    project = Project.objects.create(name="Alpha", color="#aabbcc")
    make_activity("VS Code", 9, 0, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.get(date=TARGET_DATE)
    block.project = project
    block.save()
    BlockProjectHistory.objects.create(block=block, project=project, assigned_by="manual")

    aggregate_day(TARGET_DATE)

    new_block = ActivityBlock.objects.get(date=TARGET_DATE, started_at=slot_start(9, 0))
    assert BlockProjectHistory.objects.filter(
        block=new_block, project=project, assigned_by="manual"
    ).exists()


@pytest.mark.django_db
def test_reaggregate_does_not_restore_rule_assignment():
    """Toewijzingen via regels worden NIET hersteld — die lopen via de rule engine."""
    from apps.projects.models import Project
    from apps.activities.models import BlockProjectHistory

    project = Project.objects.create(name="Alpha", color="#aabbcc")
    make_activity("VS Code", 9, 0, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.get(date=TARGET_DATE)
    block.project = project
    block.save()
    BlockProjectHistory.objects.create(block=block, project=project, assigned_by="rule")

    aggregate_day(TARGET_DATE)

    new_block = ActivityBlock.objects.get(date=TARGET_DATE, started_at=slot_start(9, 0))
    # Rule-toewijzingen worden opnieuw bepaald door de rule engine, niet hersteld uit de snapshot
    assert BlockProjectHistory.objects.filter(
        block=new_block, assigned_by="manual"
    ).count() == 0


@pytest.mark.django_db
def test_reaggregate_ignores_slot_without_new_block():
    """Als een slot na herberekening leeg is, wordt de snapshot stilzwijgend genegeerd."""
    from apps.projects.models import Project
    from apps.activities.models import BlockProjectHistory

    project = Project.objects.create(name="Alpha", color="#aabbcc")
    activity = make_activity("VS Code", 9, 0, duration_seconds=60, save=True)

    aggregate_day(TARGET_DATE)

    block = ActivityBlock.objects.get(date=TARGET_DATE)
    block.project = project
    block.save()
    BlockProjectHistory.objects.create(block=block, project=project, assigned_by="manual")

    # Verwijder de activiteit zodat het slot leeg is na herberekening
    activity.delete()

    # Mag geen fout gooien
    aggregate_day(TARGET_DATE)
    assert ActivityBlock.objects.filter(date=TARGET_DATE).count() == 0
