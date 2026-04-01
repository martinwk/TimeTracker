"""
Tests voor de rule engine functionaliteit.

Test coverage:
  - Regel matcht op app_name → ActivityMapping aangemaakt
  - Regel matcht op title_contains → ActivityMapping aangemaakt
  - Geen match → geen ActivityMapping
  - Handmatige mapping wordt niet overschreven
  - Lagere priority wint bij meerdere matchende regels
  - Idempotentie: twee keer draaien geeft zelfde resultaat
  - Inactieve regels worden genegeerd
"""

from datetime import date, datetime, timezone

import pytest
from django.db import IntegrityError

from activities.models import ActivityBlock, UniqueActivity, WindowActivity, ActivityRule
from activities.rule_engine import apply_rules
from projects.models import ActivityMapping, Project, TimeEntry


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def project_research(db):
    """Project voor onderzoek."""
    return Project.objects.create(name="Onderzoek", color="#4F86C6")


@pytest.fixture
def project_admin(db):
    """Project voor administratie."""
    return Project.objects.create(name="Administratie", color="#E8593C")


@pytest.fixture
def zotero_rule(project_research):
    """Rule: Zotero → Onderzoek project."""
    return ActivityRule.objects.create(
        project=project_research,
        match_field="app_name",
        match_value="Zotero",
        priority=10,
        is_active=True,
    )


@pytest.fixture
def vscode_rule(project_admin):
    """Rule: VS Code → Administratie project."""
    return ActivityRule.objects.create(
        project=project_admin,
        match_field="app_name",
        match_value="VS Code",
        priority=20,
        is_active=True,
    )


@pytest.fixture
def report_rule(project_research):
    """Rule: title bevat 'Report' → Onderzoek project."""
    return ActivityRule.objects.create(
        project=project_research,
        match_field="title_contains",
        match_value="Report",
        priority=5,
        is_active=True,
    )


@pytest.fixture
def activity_block(db):
    """ActivityBlock met Zotero app."""
    return ActivityBlock.objects.create(
        app_name="Zotero",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
    )


@pytest.fixture
def unique_activity_zotero(activity_block):
    """UniqueActivity in ActivityBlock."""
    return UniqueActivity.objects.create(
        block=activity_block,
        raw_title="Koersnotatie - Zotero",
        total_seconds=3600,
    )


@pytest.fixture
def window_activity_for_zotero(unique_activity_zotero):
    """WindowActivity linked to UniqueActivity."""
    start = datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc)
    activity = WindowActivity.from_log_line(start, end, "Koersnotatie - Zotero")
    activity.date = date(2026, 3, 13)
    activity.unique_activity = unique_activity_zotero
    activity.save()
    return activity


# ── Test: Rule matcht op app_name ──────────────────────────────────────────

@pytest.mark.django_db
def test_rule_matches_app_name(zotero_rule, unique_activity_zotero, window_activity_for_zotero):
    """Regel matcht op app_name → ActivityMapping aangemaakt."""
    result = apply_rules()
    assert result.mappings_created == 1
    assert result.mappings_skipped_manual == 0
    assert result.unique_activities_processed == 1

    # Controleer dat mapping aangemaakt is
    mapping = ActivityMapping.objects.get(unique_activity=unique_activity_zotero)
    assert mapping.source == ActivityMapping.SOURCE_RULE
    assert mapping.time_entry.project == zotero_rule.project


@pytest.mark.django_db
def test_rule_matches_title_contains(report_rule, project_research):
    """Regel matcht op title_contains → ActivityMapping aangemaakt."""
    block = ActivityBlock.objects.create(
        app_name="Word",
        date=date(2026, 3, 14),
        started_at=datetime(2026, 3, 14, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
    )
    ua = UniqueActivity.objects.create(
        block=block,
        raw_title="Q3 Report - Word",
        total_seconds=3600,
    )
    start = datetime(2026, 3, 14, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc)
    wa = WindowActivity.from_log_line(start, end, "Q3 Report - Word")
    wa.date = date(2026, 3, 14)
    wa.unique_activity = ua
    wa.save()

    result = apply_rules()
    assert result.mappings_created == 1

    # Mapping moet naar project_research gaan (vanwege "Report")
    mapping = ActivityMapping.objects.get(unique_activity=ua)
    assert mapping.time_entry.project == project_research


# ── Test: Geen match → geen ActivityMapping ────────────────────────────────

@pytest.mark.django_db
def test_no_rule_match_no_mapping(unique_activity_zotero, window_activity_for_zotero):
    """Geen matching rule → geen ActivityMapping aangemaakt."""
    # Geen rules gemaakt
    result = apply_rules()
    assert result.mappings_created == 0
    assert ActivityMapping.objects.count() == 0


# ── Test: Handmatige mapping wordt niet overschreven ───────────────────────

@pytest.mark.django_db
def test_manual_mapping_not_overwritten(
    zotero_rule,
    unique_activity_zotero,
    window_activity_for_zotero,
    project_admin,
):
    """Handmatige mapping wordt niet overschreven door regel."""
    # Maak manual mapping
    time_entry = TimeEntry.objects.create(
        project=project_admin,
        date=date(2026, 3, 13),
        duration_minutes=30,
    )
    manual_mapping = ActivityMapping.objects.create(
        unique_activity=unique_activity_zotero,
        time_entry=time_entry,
        source=ActivityMapping.SOURCE_MANUAL,
    )

    # Voer rules uit
    result = apply_rules()

    # Manual mapping moet behouden blijven
    assert ActivityMapping.objects.count() == 1
    assert result.mappings_skipped_manual == 1
    assert result.mappings_created == 0

    # Manual mapping is onveranderd
    manual_mapping.refresh_from_db()
    assert manual_mapping.source == ActivityMapping.SOURCE_MANUAL
    assert manual_mapping.time_entry.project == project_admin


# ── Test: Lagere priority wint bij meerdere matchende regels ────────────────

@pytest.mark.django_db
def test_lower_priority_wins(project_research, project_admin, unique_activity_zotero, window_activity_for_zotero):
    """Regel met lagere prioriteit (laag getal) wint."""
    # Maak twee regels: één met prio 5, één met prio 10
    high_prio_rule = ActivityRule.objects.create(
        project=project_admin,
        match_field="app_name",
        match_value="Zotero",
        priority=5,  # Lagere = hoger prioriteit
        is_active=True,
    )
    low_prio_rule = ActivityRule.objects.create(
        project=project_research,
        match_field="app_name",
        match_value="Zotero",
        priority=10,
        is_active=True,
    )

    result = apply_rules()
    assert result.mappings_created == 1

    # Mapping moet naar high_prio_rule.project gaan
    mapping = ActivityMapping.objects.get(unique_activity=unique_activity_zotero)
    assert mapping.time_entry.project == high_prio_rule.project


# ── Test: Idempotentie ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_idempotence(zotero_rule, unique_activity_zotero, window_activity_for_zotero):
    """Twee keer draaien geeft zelfde resultaat."""
    result1 = apply_rules()
    result2 = apply_rules()

    # Maar tweede keer: mappings_created = 0 omdat ze al bestaan (en rule-based zijn)
    assert result1.mappings_created == 1
    assert result2.mappings_created == 0  # Al gemaakt, nu verwijderd en opnieuw

    # Totaal mappings moet 1 blijven
    assert ActivityMapping.objects.count() == 1


# ── Test: Inactieve regels worden genegeerd ────────────────────────────────

@pytest.mark.django_db
def test_inactive_rules_ignored(project_research, unique_activity_zotero, window_activity_for_zotero):
    """Inactieve regels worden niet gebruikt."""
    # Maak inactive rule
    inactive_rule = ActivityRule.objects.create(
        project=project_research,
        match_field="app_name",
        match_value="Zotero",
        priority=10,
        is_active=False,
    )

    result = apply_rules()

    # Geen mapping omdat regel inactief is
    assert result.mappings_created == 0
    assert ActivityMapping.objects.count() == 0


# ── Test: Date filtering ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_date_filtering(zotero_rule, unique_activity_zotero, window_activity_for_zotero):
    """apply_rules filtert op datum."""
    # ActivityBlock op 2026-03-13
    # Voer rules uit voor andere datum
    result = apply_rules(date_from=date(2026, 3, 14), date_to=date(2026, 3, 14))

    # Geen mapping omdat datum niet matcht
    assert result.mappings_created == 0
    assert ActivityMapping.objects.count() == 0

    # Voer rules uit voor juiste datum
    result = apply_rules(date_from=date(2026, 3, 13), date_to=date(2026, 3, 13))
    assert result.mappings_created == 1


# ── Test: Multiple matches first match wins ────────────────────────────────

@pytest.mark.django_db
def test_first_matching_rule_wins(project_research, project_admin):
    """Bij meerdere match: eerste in prioriteit-volgorde wint."""
    # Maak twee rules met verschillende prioriteiten
    rule_prio_10 = ActivityRule.objects.create(
        project=project_admin,
        match_field="title_contains",
        match_value="document",
        priority=10,
        is_active=True,
    )
    rule_prio_5 = ActivityRule.objects.create(
        project=project_research,
        match_field="title_contains",
        match_value="document",
        priority=5,  # Hoger prioriteit
        is_active=True,
    )

    # Maak UA met "document" in titel
    block = ActivityBlock.objects.create(
        app_name="Editor",
        date=date(2026, 3, 15),
        started_at=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
    )
    ua = UniqueActivity.objects.create(
        block=block,
        raw_title="document.txt - Editor",
        total_seconds=3600,
    )
    wa = WindowActivity.from_log_line(
        datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc),
        "document.txt - Editor",
    )
    wa.date = date(2026, 3, 15)
    wa.unique_activity = ua
    wa.save()

    result = apply_rules()
    assert result.mappings_created == 1

    # Mapping moet naar rule_prio_5.project gaan (hoger prioriteit)
    mapping = ActivityMapping.objects.get(unique_activity=ua)
    assert mapping.time_entry.project == rule_prio_5.project
