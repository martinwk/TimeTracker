"""
Tests voor de rule engine functionaliteit.

Test coverage:
  - Regel matcht op app_name → Project aan block toegewezen
  - Regel matcht op title_contains → Project aan block toegewezen
  - Geen match → project blijft None
  - Lagere priority wint bij meerdere matchende regels
  - Idempotentie: twee keer draaien geeft zelfde resultaat
  - Inactieve regels worden genegeerd
"""

from datetime import date, datetime, timezone

import pytest

from activities.models import ActivityBlock, UniqueActivity, WindowActivity, ActivityRule
from activities.rule_engine import apply_rules
from projects.models import Project


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
    """ActivityBlock met Zotero app (project=None initially)."""
    return ActivityBlock.objects.create(
        app_name="Zotero",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=None,
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
def test_rule_matches_app_name(zotero_rule, activity_block, unique_activity_zotero, window_activity_for_zotero):
    """Regel matcht op app_name → Project aan block toegewezen."""
    assert activity_block.project is None

    result = apply_rules()
    assert result.blocks_assigned == 1
    assert result.blocks_processed == 1

    # Controleer dat project toegewezen is
    activity_block.refresh_from_db()
    assert activity_block.project == zotero_rule.project


@pytest.mark.django_db
def test_rule_matches_title_contains(report_rule, project_research):
    """Regel matcht op title_contains → Project aan block toegewezen."""
    block = ActivityBlock.objects.create(
        app_name="Word",
        date=date(2026, 3, 14),
        started_at=datetime(2026, 3, 14, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=None,
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
    assert result.blocks_assigned == 1

    # Block project moet naar project_research gaan (vanwege "Report")
    block.refresh_from_db()
    assert block.project == project_research


# ── Test: Geen match → geen project toewijzing ────────────────────────────

@pytest.mark.django_db
def test_no_rule_match_no_assignment(unique_activity_zotero, window_activity_for_zotero, activity_block):
    """Geen matching rule → project blijft None."""
    # Geen rules gemaakt
    result = apply_rules()
    assert result.blocks_assigned == 0
    activity_block.refresh_from_db()
    assert activity_block.project is None


# ── Test: Block met bestaand project wordt niet overschreven ───────────────

@pytest.mark.django_db
def test_block_with_project_not_overwritten(
    zotero_rule,
    project_admin,
):
    """Block met bestaand project wordt niet verwerkt."""
    # Maak block met al ingesteld project
    block = ActivityBlock.objects.create(
        app_name="Zotero",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=project_admin,  # Al ingesteld
    )
    ua = UniqueActivity.objects.create(
        block=block,
        raw_title="Koersnotatie - Zotero",
        total_seconds=3600,
    )
    start = datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc)
    wa = WindowActivity.from_log_line(start, end, "Koersnotatie - Zotero")
    wa.date = date(2026, 3, 13)
    wa.unique_activity = ua
    wa.save()

    # Voer rules uit
    result = apply_rules()

    # Block moet onveranderd blijven (project_admin)
    assert result.blocks_assigned == 0  # Niet verwerkt want project != None
    block.refresh_from_db()
    assert block.project == project_admin


# ── Test: Lagere priority wint bij meerdere matchende regels ────────────────

@pytest.mark.django_db
def test_lower_priority_wins(project_research, project_admin):
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

    block = ActivityBlock.objects.create(
        app_name="Zotero",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=None,
    )
    ua = UniqueActivity.objects.create(
        block=block,
        raw_title="Koersnotatie - Zotero",
        total_seconds=3600,
    )
    wa = WindowActivity.from_log_line(
        datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        "Koersnotatie - Zotero",
    )
    wa.date = date(2026, 3, 13)
    wa.unique_activity = ua
    wa.save()

    result = apply_rules()
    assert result.blocks_assigned == 1

    # Block project moet naar high_prio_rule.project gaan
    block.refresh_from_db()
    assert block.project == high_prio_rule.project


# ── Test: Idempotentie ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_idempotence(zotero_rule, activity_block, unique_activity_zotero, window_activity_for_zotero):
    """Twee keer draaien geeft zelfde resultaat."""
    result1 = apply_rules()
    result2 = apply_rules()

    # Eerste keer: 1 block assigned
    assert result1.blocks_assigned == 1

    # Tweede keer: 0 blocks assigned (omdat ze al project hebben)
    assert result2.blocks_assigned == 0

    # Block project moet juist zijn
    activity_block.refresh_from_db()
    assert activity_block.project == zotero_rule.project


# ── Test: Inactieve regels worden genegeerd ────────────────────────────────

@pytest.mark.django_db
def test_inactive_rules_ignored(project_research, activity_block, unique_activity_zotero, window_activity_for_zotero):
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

    # Geen toewijzing omdat regel inactief is
    assert result.blocks_assigned == 0
    activity_block.refresh_from_db()
    assert activity_block.project is None


# ── Test: Date filtering ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_date_filtering(zotero_rule, activity_block, unique_activity_zotero, window_activity_for_zotero):
    """apply_rules filtert op datum."""
    # ActivityBlock op 2026-03-13
    # Voer rules uit voor andere datum
    result = apply_rules(date_from=date(2026, 3, 14), date_to=date(2026, 3, 14))

    # Geen toewijzing omdat datum niet matcht
    assert result.blocks_assigned == 0
    activity_block.refresh_from_db()
    assert activity_block.project is None

    # Voer rules uit voor juiste datum
    result = apply_rules(date_from=date(2026, 3, 13), date_to=date(2026, 3, 13))
    assert result.blocks_assigned == 1
    activity_block.refresh_from_db()
    assert activity_block.project == zotero_rule.project


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

    # Maak block met "document" in titel
    block = ActivityBlock.objects.create(
        app_name="Editor",
        date=date(2026, 3, 15),
        started_at=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=None,
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
    assert result.blocks_assigned == 1

    # Block project moet naar rule_prio_5.project gaan (hoger prioriteit)
    block.refresh_from_db()
    assert block.project == rule_prio_5.project


# ── Test: Smart Rules (Phase 2) ────────────────────────────────────────────

@pytest.mark.django_db
def test_recent_project_rule(project_research, project_admin):
    """Recent project rule → use project from recent same-app block."""
    # First, create a block assigned to project_research with app VSCode
    old_block = ActivityBlock.objects.create(
        app_name="VSCode",
        date=date(2026, 3, 10),
        started_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=project_research,
    )
    
    # Create a rule: recent_project for VSCode
    recent_rule = ActivityRule.objects.create(
        project=project_admin,  # Not used, just for rule config
        match_field="recent_project",
        match_value="VSCode",
        priority=15,
        is_active=True,
    )
    
    # Create new unassigned block with same app
    new_block = ActivityBlock.objects.create(
        app_name="VSCode",
        date=date(2026, 3, 15),
        started_at=datetime(2026, 3, 15, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=None,
    )
    ua = UniqueActivity.objects.create(
        block=new_block,
        raw_title="settings.json - VSCode",
        total_seconds=3600,
    )
    wa = WindowActivity.from_log_line(
        datetime(2026, 3, 15, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
        "settings.json - VSCode",
    )
    wa.date = date(2026, 3, 15)
    wa.unique_activity = ua
    wa.save()
    
    result = apply_rules()
    assert result.blocks_assigned == 1
    
    # New block should get project_research (recent project for VSCode)
    new_block.refresh_from_db()
    assert new_block.project == project_research


@pytest.mark.django_db
def test_dominant_activity_rule(project_research, project_admin):
    """Dominant activity rule → use project from blocks with same activity title."""
    # Create old block with specific activity title assigned to research
    old_block = ActivityBlock.objects.create(
        app_name="Word",
        date=date(2026, 3, 10),
        started_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=project_research,
    )
    old_ua = UniqueActivity.objects.create(
        block=old_block,
        raw_title="Literature Review - Word",
        total_seconds=3600,
    )
    
    # Create rule for dominant_activity
    dom_rule = ActivityRule.objects.create(
        project=project_admin,  # Not used
        match_field="dominant_activity",
        match_value="Literature Review - Word",
        priority=12,
        is_active=True,
    )
    
    # Create new unassigned block with same dominant activity
    new_block = ActivityBlock.objects.create(
        app_name="Word",
        date=date(2026, 3, 15),
        started_at=datetime(2026, 3, 15, 14, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=None,
    )
    new_ua = UniqueActivity.objects.create(
        block=new_block,
        raw_title="Literature Review - Word",
        total_seconds=3600,
    )
    wa = WindowActivity.from_log_line(
        datetime(2026, 3, 15, 14, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        "Literature Review - Word",
    )
    wa.date = date(2026, 3, 15)
    wa.unique_activity = new_ua
    wa.save()
    
    result = apply_rules()
    assert result.blocks_assigned == 1
    
    # New block should get project_research (used for this activity title)
    new_block.refresh_from_db()
    assert new_block.project == project_research


@pytest.mark.django_db
def test_history_tracked_on_assignment(project_research, activity_block, unique_activity_zotero, window_activity_for_zotero):
    """Assignment via rule creates BlockProjectHistory entry."""
    from activities.models import BlockProjectHistory
    
    rule = ActivityRule.objects.create(
        project=project_research,
        match_field="app_name",
        match_value="Zotero",
        priority=10,
        is_active=True,
    )
    
    apply_rules()
    
    # Check history was recorded
    history = BlockProjectHistory.objects.filter(block=activity_block)
    assert history.exists()
    assert history.count() == 1
    
    hist_entry = history.first()
    assert hist_entry.project == project_research
    assert hist_entry.assigned_by == "rule"
