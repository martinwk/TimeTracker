from datetime import datetime, timezone

import pytest
from rest_framework.test import APIClient

from apps.activities.models import WindowActivity, ActivityBlock, UniqueActivity, ActivityRule, detect_noise, extract_app_name


# ── extract_app_name ─────────────────────────────────────────────────────────

def test_extract_app_name_zotero():
    assert extract_app_name("Koers zetten - Zotero") == "Zotero"

def test_extract_app_name_firefox_em_dash():
    assert extract_app_name("Google — Mozilla Firefox") == "Mozilla Firefox"

def test_extract_app_name_multiple_dashes():
    assert extract_app_name(
        "track_window_log.ahk - AutoHotkey - Visual Studio Code"
    ) == "Visual Studio Code"

def test_extract_app_name_no_separator():
    """Zonder scheidingsteken is de hele titel de app-naam."""
    assert extract_app_name("Notepad") == "Notepad"

def test_extract_app_name_strips_whitespace():
    assert extract_app_name("  Document - Word  ") == "Word"


# ── detect_noise ─────────────────────────────────────────────────────────────

def test_detect_noise_idle():
    assert detect_noise("Idle") is True

def test_detect_noise_program_manager():
    assert detect_noise("Program Manager") is True

def test_detect_noise_task_switching():
    assert detect_noise("Task Switching") is True

def test_detect_noise_desktop():
    assert detect_noise("Desktop") is True

def test_detect_noise_firefox_is_not_noise():
    assert detect_noise("Mozilla Firefox") is False

def test_detect_noise_vscode_is_not_noise():
    assert detect_noise("track_window_log.ahk - AutoHotkey - Visual Studio Code") is False

def test_detect_noise_case_insensitive():
    assert detect_noise("IDLE") is True
    assert detect_noise("program manager") is True


# ── WindowActivity.from_log_line ─────────────────────────────────────────────

START = datetime(2026, 3, 13, 9, 14, 0, tzinfo=timezone.utc)
END   = datetime(2026, 3, 13, 9, 14, 6, tzinfo=timezone.utc)
TITLE = "Koers zetten richting digitale autonomie - Lockefeer - Zotero"


@pytest.fixture
def zotero_activity():
    return WindowActivity.from_log_line(START, END, TITLE)


def test_from_log_line_app_name(zotero_activity):
    assert zotero_activity.app_name == "Zotero"

def test_from_log_line_is_not_noise(zotero_activity):
    assert zotero_activity.is_noise is False

def test_from_log_line_duration(zotero_activity):
    assert zotero_activity.duration_seconds == 6

def test_from_log_line_date(zotero_activity):
    assert str(zotero_activity.date) == "2026-03-13"

def test_from_log_line_raw_title_preserved(zotero_activity):
    assert zotero_activity.raw_title == TITLE


@pytest.mark.django_db
def test_from_log_line_save_and_count(zotero_activity):
    zotero_activity.save()
    assert WindowActivity.objects.count() == 1


def test_from_log_line_noise_activity():
    idle = WindowActivity.from_log_line(START, END, "Idle")
    assert idle.is_noise is True
    assert idle.app_name == "Idle"

def test_from_log_line_zero_duration_clamped():
    """Negatieve duur (klokafwijking) wordt naar 0 geklampt."""
    activity = WindowActivity.from_log_line(END, START, "Test")
    assert activity.duration_seconds == 0


# ── API: WindowActivityViewSet ────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def window_activity(db):
    """Create a saved WindowActivity for API tests."""
    start = datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 3, 13, 9, 30, tzinfo=timezone.utc)
    activity = WindowActivity.from_log_line(start, end, "Test Document - VS Code")
    activity.save()
    return activity


@pytest.mark.django_db
def test_window_activity_list(api_client, window_activity):
    """GET /api/window-activities/ should return all activities."""
    response = api_client.get("/api/activities/window-activities/")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == window_activity.id


@pytest.mark.django_db
def test_window_activity_detail(api_client, window_activity):
    """GET /api/window-activities/{id}/ should return single activity."""
    response = api_client.get(f"/api/activities/window-activities/{window_activity.id}/")
    assert response.status_code == 200
    assert response.data["app_name"] == "VS Code"
    assert response.data["is_noise"] is False


@pytest.mark.django_db
def test_window_activity_filter_by_date(api_client, window_activity):
    """Filter activities by date."""
    response = api_client.get("/api/activities/window-activities/?date=2026-03-13")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_window_activity_filter_by_app_name(api_client, window_activity):
    """Filter activities by app_name."""
    response = api_client.get("/api/activities/window-activities/?app_name=VS Code")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_window_activity_filter_by_is_noise(api_client, window_activity):
    """Filter activities by is_noise."""
    response = api_client.get("/api/activities/window-activities/?is_noise=false")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_window_activity_create(api_client):
    """POST to create a new WindowActivity."""
    data = {
        "started_at": "2026-03-13T09:00:00Z",
        "ended_at": "2026-03-13T09:30:00Z",
        "duration_seconds": 1800,
        "raw_title": "Test - App",
        "app_name": "App",
        "date": "2026-03-13",
        "is_noise": False,
    }
    response = api_client.post("/api/activities/window-activities/", data)
    assert response.status_code == 201
    assert WindowActivity.objects.count() == 1


@pytest.mark.django_db
def test_window_activity_update(api_client, window_activity):
    """PUT to update is_noise field."""
    data = {"is_noise": True}
    response = api_client.patch(f"/api/activities/window-activities/{window_activity.id}/", data)
    assert response.status_code == 200
    window_activity.refresh_from_db()
    assert window_activity.is_noise is True


@pytest.mark.django_db
def test_window_activity_delete(api_client, window_activity):
    """DELETE to remove an activity."""
    response = api_client.delete(f"/api/activities/window-activities/{window_activity.id}/")
    assert response.status_code == 204
    assert WindowActivity.objects.count() == 0


# ── API: ActivityBlockViewSet ─────────────────────────────────────────────────

@pytest.fixture
def activity_block(db):
    """Create a saved ActivityBlock."""
    block = ActivityBlock.objects.create(
        app_name="VS Code",
        date=datetime(2026, 3, 13, tzinfo=timezone.utc).date(),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 30, tzinfo=timezone.utc),
        total_seconds=5400,
        activity_count=10,
        block_minutes=30,
    )
    return block


@pytest.mark.django_db
def test_activity_block_list(api_client, activity_block):
    """GET /api/activity-blocks/ should return all blocks."""
    response = api_client.get("/api/activities/activity-blocks/")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_activity_block_detail(api_client, activity_block):
    """GET /api/activity-blocks/{id}/ should return block with computed fields."""
    response = api_client.get(f"/api/activities/activity-blocks/{activity_block.id}/")
    assert response.status_code == 200
    assert response.data["app_name"] == "VS Code"
    assert "total_minutes" in response.data
    assert response.data["total_minutes"] == 90.0


@pytest.mark.django_db
def test_activity_block_filter_by_date(api_client, activity_block):
    """Filter blocks by date."""
    response = api_client.get("/api/activities/activity-blocks/?date=2026-03-13")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_activity_block_create(api_client):
    """POST to create a new ActivityBlock."""
    data = {
        "app_name": "Firefox",
        "date": "2026-03-13",
        "started_at": "2026-03-13T09:00:00Z",
        "ended_at": "2026-03-13T10:00:00Z",
        "total_seconds": 3600,
        "activity_count": 5,
        "block_minutes": 30,
    }
    response = api_client.post("/api/activities/activity-blocks/", data)
    assert response.status_code == 201


# ── API: UniqueActivityViewSet ────────────────────────────────────────────────

@pytest.fixture
def unique_activity(activity_block):
    """Create a UniqueActivity linked to ActivityBlock."""
    ua = UniqueActivity.objects.create(
        block=activity_block,
        raw_title="test.py - VS Code",
        total_seconds=3600,
    )
    return ua


@pytest.mark.django_db
def test_unique_activity_list(api_client, unique_activity):
    """GET /api/unique-activities/ should return all unique activities."""
    response = api_client.get("/api/activities/unique-activities/")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_unique_activity_detail(api_client, unique_activity):
    """GET /api/unique-activities/{id}/ should return unique activity."""
    response = api_client.get(f"/api/activities/unique-activities/{unique_activity.id}/")
    assert response.status_code == 200
    assert response.data["raw_title"] == "test.py - VS Code"
    assert "total_minutes" in response.data


@pytest.mark.django_db
def test_unique_activity_filter_by_block(api_client, unique_activity, activity_block):
    """Filter unique activities by block."""
    response = api_client.get(f"/api/activities/unique-activities/?block={activity_block.id}")
    assert response.status_code == 200
    assert response.data["count"] == 1


# ── API: ActivityRuleViewSet ──────────────────────────────────────────────────

@pytest.fixture
def project_for_rule(db):
    from apps.projects.models import Project
    return Project.objects.create(name="Test Project", color="#000000")


@pytest.fixture
def activity_rule(project_for_rule):
    """Create an ActivityRule."""
    rule = ActivityRule.objects.create(
        project=project_for_rule,
        match_field="app_name",
        match_value="VS Code",
        priority=10,
        is_active=True,
    )
    return rule


@pytest.mark.django_db
def test_activity_rule_list(api_client, activity_rule):
    """GET /api/activity-rules/ should return all rules."""
    response = api_client.get("/api/activities/activity-rules/")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_activity_rule_detail(api_client, activity_rule):
    """GET /api/activity-rules/{id}/ should return rule with display values."""
    response = api_client.get(f"/api/activities/activity-rules/{activity_rule.id}/")
    assert response.status_code == 200
    assert response.data["match_field"] == "app_name"
    assert response.data["match_value"] == "VS Code"
    assert "match_field_display" in response.data


@pytest.mark.django_db
def test_activity_rule_filter_by_project(api_client, activity_rule, project_for_rule):
    """Filter rules by project."""
    response = api_client.get(f"/api/activities/activity-rules/?project={project_for_rule.id}")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_activity_rule_filter_by_is_active(api_client, activity_rule):
    """Filter rules by is_active."""
    response = api_client.get("/api/activities/activity-rules/?is_active=true")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_activity_rule_create(api_client, project_for_rule):
    """POST to create a new ActivityRule."""
    data = {
        "project": project_for_rule.id,
        "match_field": "title_contains",
        "match_value": "Report",
        "priority": 5,
        "is_active": True,
    }
    response = api_client.post("/api/activities/activity-rules/", data)
    assert response.status_code == 201
    assert ActivityRule.objects.count() == 1


@pytest.mark.django_db
def test_activity_rule_update(api_client, activity_rule):
    """PATCH to update priority."""
    data = {"priority": 20}
    response = api_client.patch(f"/api/activities/activity-rules/{activity_rule.id}/", data)
    assert response.status_code == 200
    activity_rule.refresh_from_db()
    assert activity_rule.priority == 20


# ── API: ActivityBlock — ended_at herberekening (stap 3) ─────────────────────

@pytest.mark.django_db
def test_patch_started_at_updates_ended_at(api_client, activity_block):
    """PATCH started_at → ended_at = started_at + total_seconds."""
    new_start = "2026-03-13T10:00:00Z"
    response = api_client.patch(
        f"/api/activities/activity-blocks/{activity_block.id}/",
        {"started_at": new_start},
        format="json",
    )
    assert response.status_code == 200
    activity_block.refresh_from_db()
    # total_seconds was 5400 (90 min), started_at + 5400s = 11:30
    assert activity_block.started_at == datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc)
    assert activity_block.ended_at   == datetime(2026, 3, 13, 11, 30, tzinfo=timezone.utc)


@pytest.mark.django_db
def test_patch_total_seconds_updates_ended_at(api_client, activity_block):
    """PATCH total_seconds → ended_at = started_at + nieuw total_seconds."""
    response = api_client.patch(
        f"/api/activities/activity-blocks/{activity_block.id}/",
        {"total_seconds": 1800},  # 30 min
        format="json",
    )
    assert response.status_code == 200
    activity_block.refresh_from_db()
    # started_at was 09:00, + 1800s = 09:30
    assert activity_block.ended_at == datetime(2026, 3, 13, 9, 30, tzinfo=timezone.utc)


@pytest.mark.django_db
def test_patch_started_at_and_total_seconds_together(api_client, activity_block):
    """PATCH started_at + total_seconds samen → ended_at correct."""
    response = api_client.patch(
        f"/api/activities/activity-blocks/{activity_block.id}/",
        {"started_at": "2026-03-13T14:00:00Z", "total_seconds": 3600},
        format="json",
    )
    assert response.status_code == 200
    activity_block.refresh_from_db()
    assert activity_block.ended_at == datetime(2026, 3, 13, 15, 0, tzinfo=timezone.utc)


# ── API: ActivityBlock — nested project (stap 1) ──────────────────────────────

@pytest.fixture
def project_alpha(db):
    from apps.projects.models import Project
    return Project.objects.create(name="Alpha", color="#6366f1")


@pytest.fixture
def activity_block_with_project(db, project_alpha):
    from datetime import date
    return ActivityBlock.objects.create(
        app_name="VS Code",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 30, tzinfo=timezone.utc),
        total_seconds=5400,
        activity_count=10,
        block_minutes=30,
        project=project_alpha,
    )


# ── API: ActivityBlock — handmatig aanmaken met defaults (stap 5) ────────────

@pytest.mark.django_db
def test_create_block_minimal_fields(api_client):
    """POST met alleen started_at + total_seconds maakt een geldig blok aan."""
    response = api_client.post(
        "/api/activities/activity-blocks/",
        {"started_at": "2026-03-13T09:00:00Z", "total_seconds": 900},
        format="json",
    )
    assert response.status_code == 201
    block = ActivityBlock.objects.get(pk=response.data["id"])
    assert block.total_seconds == 900
    assert block.ended_at == datetime(2026, 3, 13, 9, 15, tzinfo=timezone.utc)
    assert block.app_name == "handmatig"
    assert block.activity_count == 1
    assert block.block_minutes == 15


@pytest.mark.django_db
def test_create_block_with_project(api_client, project_alpha):
    """POST met project_id koppelt direct het project."""
    response = api_client.post(
        "/api/activities/activity-blocks/",
        {
            "started_at": "2026-03-13T10:00:00Z",
            "total_seconds": 1800,
            "project_id": project_alpha.id,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["project"]["id"] == project_alpha.id


@pytest.mark.django_db
def test_create_block_sets_date_from_started_at(api_client):
    """date-veld wordt automatisch afgeleid van started_at."""
    response = api_client.post(
        "/api/activities/activity-blocks/",
        {"started_at": "2026-03-15T08:00:00Z", "total_seconds": 600},
        format="json",
    )
    assert response.status_code == 201
    block = ActivityBlock.objects.get(pk=response.data["id"])
    from datetime import date
    assert block.date == date(2026, 3, 15)


@pytest.mark.django_db
def test_create_block_requires_started_at(api_client):
    """POST zonder started_at geeft 400."""
    response = api_client.post(
        "/api/activities/activity-blocks/",
        {"total_seconds": 900},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_create_block_requires_total_seconds(api_client):
    """POST zonder total_seconds geeft 400."""
    response = api_client.post(
        "/api/activities/activity-blocks/",
        {"started_at": "2026-03-13T09:00:00Z"},
        format="json",
    )
    assert response.status_code == 400


# ── API: ActivityBlock — bulk-assign (stap 4) ────────────────────────────────

@pytest.fixture
def two_unassigned_blocks(db):
    from datetime import date
    blocks = []
    for hour in (9, 11):
        blocks.append(ActivityBlock.objects.create(
            app_name="VS Code",
            date=date(2026, 3, 13),
            started_at=datetime(2026, 3, 13, hour, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 3, 13, hour + 1, 0, tzinfo=timezone.utc),
            total_seconds=3600,
            activity_count=1,
            block_minutes=15,
        ))
    return blocks


@pytest.mark.django_db
def test_bulk_assign_sets_project_on_all_blocks(api_client, two_unassigned_blocks, project_alpha):
    """POST assign/ wijst een project toe aan meerdere blokken tegelijk."""
    ids = [b.id for b in two_unassigned_blocks]
    response = api_client.post(
        "/api/activities/activity-blocks/assign/",
        {"block_ids": ids, "project_id": project_alpha.id},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["assigned"] == 2
    for block in two_unassigned_blocks:
        block.refresh_from_db()
        assert block.project_id == project_alpha.id


@pytest.mark.django_db
def test_bulk_assign_clears_project_with_null(api_client, activity_block_with_project):
    """POST assign/ met project_id=null verwijdert de koppeling."""
    response = api_client.post(
        "/api/activities/activity-blocks/assign/",
        {"block_ids": [activity_block_with_project.id], "project_id": None},
        format="json",
    )
    assert response.status_code == 200
    activity_block_with_project.refresh_from_db()
    assert activity_block_with_project.project is None


@pytest.mark.django_db
def test_bulk_assign_ignores_unknown_ids(api_client, project_alpha):
    """Onbekende block_ids worden stilzwijgend genegeerd."""
    response = api_client.post(
        "/api/activities/activity-blocks/assign/",
        {"block_ids": [99999], "project_id": project_alpha.id},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["assigned"] == 0


@pytest.mark.django_db
def test_bulk_assign_requires_block_ids(api_client, project_alpha):
    """Ontbrekend block_ids-veld geeft 400."""
    response = api_client.post(
        "/api/activities/activity-blocks/assign/",
        {"project_id": project_alpha.id},
        format="json",
    )
    assert response.status_code == 400


# ── API: ActivityBlock — datumbereikfilter (stap 2) ──────────────────────────

@pytest.fixture
def three_blocks_on_different_days(db):
    """Drie blokken op drie opeenvolgende dagen."""
    from datetime import date
    days = [date(2026, 3, 13), date(2026, 3, 14), date(2026, 3, 15)]
    blocks = []
    for d in days:
        dt = datetime(d.year, d.month, d.day, 9, 0, tzinfo=timezone.utc)
        blocks.append(ActivityBlock.objects.create(
            app_name="VS Code",
            date=d,
            started_at=dt,
            ended_at=datetime(d.year, d.month, d.day, 10, 0, tzinfo=timezone.utc),
            total_seconds=3600,
            activity_count=1,
            block_minutes=15,
        ))
    return blocks


@pytest.mark.django_db
def test_activity_block_filter_date_from(api_client, three_blocks_on_different_days):
    """?date_from=2026-03-14 geeft alleen blokken vanaf die datum."""
    response = api_client.get("/api/activities/activity-blocks/?date_from=2026-03-14")
    assert response.status_code == 200
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_activity_block_filter_date_to(api_client, three_blocks_on_different_days):
    """?date_to=2026-03-14 geeft alleen blokken t/m die datum."""
    response = api_client.get("/api/activities/activity-blocks/?date_to=2026-03-14")
    assert response.status_code == 200
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_activity_block_filter_date_range(api_client, three_blocks_on_different_days):
    """?date_from=…&date_to=… geeft blokken binnen het bereik."""
    response = api_client.get(
        "/api/activities/activity-blocks/?date_from=2026-03-13&date_to=2026-03-14"
    )
    assert response.status_code == 200
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_activity_block_filter_date_from_to_combined_with_date(api_client, three_blocks_on_different_days):
    """?date=… (exacte dag) werkt nog steeds naast de nieuwe filters."""
    response = api_client.get("/api/activities/activity-blocks/?date=2026-03-13")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_activity_block_project_is_nested_object(api_client, activity_block_with_project, project_alpha):
    """project-veld geeft {id, name, color} terug, geen integer."""
    response = api_client.get(f"/api/activities/activity-blocks/{activity_block_with_project.id}/")
    assert response.status_code == 200
    project_data = response.data["project"]
    assert isinstance(project_data, dict), f"verwacht dict, kreeg: {project_data!r}"
    assert project_data["id"] == project_alpha.id
    assert project_data["name"] == "Alpha"
    assert project_data["color"] == "#6366f1"


@pytest.mark.django_db
def test_activity_block_no_project_returns_null(api_client, activity_block):
    """project-veld is null als er geen project is toegewezen."""
    response = api_client.get(f"/api/activities/activity-blocks/{activity_block.id}/")
    assert response.status_code == 200
    assert response.data["project"] is None


@pytest.mark.django_db
def test_activity_block_patch_assigns_project_via_project_id(api_client, activity_block, project_alpha):
    """PATCH met project_id wijst een project toe aan het blok."""
    response = api_client.patch(
        f"/api/activities/activity-blocks/{activity_block.id}/",
        {"project_id": project_alpha.id},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["project"]["id"] == project_alpha.id
    assert response.data["project"]["name"] == "Alpha"


@pytest.mark.django_db
def test_activity_block_patch_removes_project(api_client, activity_block_with_project):
    """PATCH met project_id=null verwijdert de projectkoppeling."""
    response = api_client.patch(
        f"/api/activities/activity-blocks/{activity_block_with_project.id}/",
        {"project_id": None},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["project"] is None


# ── API: ActivityBlock — bulk upsert (stap 1: create + update) ───────────────

@pytest.mark.django_db
def test_bulk_upsert_creates_new_block(api_client):
    """POST bulk/ zonder id maakt een nieuw blok aan."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{"started_at": "2026-03-13T09:00:00Z", "total_seconds": 900}]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["created"] == 1
    assert response.data["updated"] == 0
    assert ActivityBlock.objects.count() == 1


@pytest.mark.django_db
def test_bulk_upsert_updates_existing_block(api_client, activity_block):
    """POST bulk/ met bestaand id werkt het blok bij."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{
            "id": activity_block.id,
            "started_at": "2026-03-13T10:00:00Z",
            "total_seconds": 1800,
        }]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["created"] == 0
    assert response.data["updated"] == 1
    activity_block.refresh_from_db()
    assert activity_block.total_seconds == 1800


@pytest.mark.django_db
def test_bulk_upsert_update_recalculates_ended_at(api_client, activity_block):
    """Bijgewerkt blok herberekent ended_at automatisch."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{
            "id": activity_block.id,
            "started_at": "2026-03-13T10:00:00Z",
            "total_seconds": 1800,
        }]},
        format="json",
    )
    assert response.status_code == 200
    activity_block.refresh_from_db()
    assert activity_block.ended_at == datetime(2026, 3, 13, 10, 30, tzinfo=timezone.utc)


@pytest.mark.django_db
def test_bulk_upsert_mixed_create_and_update(api_client, activity_block):
    """POST bulk/ met mix van nieuwe en bestaande blokken."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [
            {"id": activity_block.id, "started_at": "2026-03-13T09:00:00Z", "total_seconds": 900},
            {"started_at": "2026-03-13T11:00:00Z", "total_seconds": 1800},
        ]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["created"] == 1
    assert response.data["updated"] == 1
    assert ActivityBlock.objects.count() == 2


@pytest.mark.django_db
def test_bulk_upsert_unknown_id_treated_as_create(api_client):
    """Blok met id dat niet bestaat in de DB wordt aangemaakt als nieuw blok."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{
            "id": 999999999,
            "started_at": "2026-03-13T09:00:00Z",
            "total_seconds": 900,
        }]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["created"] == 1
    assert response.data["updated"] == 0


@pytest.mark.django_db
def test_bulk_upsert_assigns_project(api_client, project_alpha):
    """project_id in een blok wordt correct toegewezen."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{
            "started_at": "2026-03-13T09:00:00Z",
            "total_seconds": 900,
            "project_id": project_alpha.id,
        }]},
        format="json",
    )
    assert response.status_code == 200
    block = ActivityBlock.objects.get()
    assert block.project_id == project_alpha.id


@pytest.mark.django_db
def test_bulk_upsert_clears_project_with_null(api_client, activity_block_with_project):
    """project_id=null verwijdert bestaande projectkoppeling bij update."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{
            "id": activity_block_with_project.id,
            "started_at": "2026-03-13T09:00:00Z",
            "total_seconds": 900,
            "project_id": None,
        }]},
        format="json",
    )
    assert response.status_code == 200
    activity_block_with_project.refresh_from_db()
    assert activity_block_with_project.project is None


@pytest.mark.django_db
def test_bulk_upsert_empty_list_is_valid(api_client):
    """Lege blocks-lijst is geldig en geeft 0 created/updated terug."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": []},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["created"] == 0
    assert response.data["updated"] == 0


@pytest.mark.django_db
def test_bulk_upsert_missing_blocks_key_gives_400(api_client):
    """Ontbrekend blocks-veld geeft 400."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_bulk_upsert_missing_started_at_gives_400(api_client):
    """Blok zonder started_at geeft 400."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{"total_seconds": 900}]},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_bulk_upsert_missing_total_seconds_gives_400(api_client):
    """Blok zonder total_seconds geeft 400."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{"started_at": "2026-03-13T09:00:00Z"}]},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_bulk_upsert_invalid_project_id_gives_400(api_client):
    """Onbekend project_id geeft 400."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{
            "started_at": "2026-03-13T09:00:00Z",
            "total_seconds": 900,
            "project_id": 99999,
        }]},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_bulk_upsert_returns_saved_blocks(api_client):
    """Response bevat de opgeslagen blokken met hun server-id's."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{"started_at": "2026-03-13T09:00:00Z", "total_seconds": 900}]},
        format="json",
    )
    assert response.status_code == 200
    assert len(response.data["blocks"]) == 1
    assert "id" in response.data["blocks"][0]
    assert response.data["blocks"][0]["total_seconds"] == 900


# ── API: ActivityBlock — bulk upsert (stap 2: deletes) ───────────────────────

@pytest.mark.django_db
def test_bulk_upsert_deletes_blocks_in_deleted_ids(api_client, two_unassigned_blocks):
    """deleted_ids verwijdert de opgegeven blokken uit de database."""
    ids = [b.id for b in two_unassigned_blocks]
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [], "deleted_ids": ids},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["deleted"] == 2
    assert ActivityBlock.objects.count() == 0


@pytest.mark.django_db
def test_bulk_upsert_delete_unknown_ids_ignored(api_client):
    """Onbekende id's in deleted_ids worden stilzwijgend genegeerd."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [], "deleted_ids": [99999, 88888]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["deleted"] == 0


@pytest.mark.django_db
def test_bulk_upsert_empty_deleted_ids_is_valid(api_client):
    """Lege deleted_ids-lijst is geldig."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [], "deleted_ids": []},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["deleted"] == 0


@pytest.mark.django_db
def test_bulk_upsert_missing_deleted_ids_defaults_to_no_deletes(api_client, activity_block):
    """Ontbrekend deleted_ids-veld resulteert in geen verwijderingen."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": []},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["deleted"] == 0
    assert ActivityBlock.objects.count() == 1


@pytest.mark.django_db
def test_bulk_upsert_delete_and_create_in_one_call(api_client, activity_block):
    """Verwijdering en aanmaak kunnen in dezelfde call."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {
            "blocks": [{"started_at": "2026-03-13T11:00:00Z", "total_seconds": 900}],
            "deleted_ids": [activity_block.id],
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.data["created"] == 1
    assert response.data["deleted"] == 1
    assert ActivityBlock.objects.count() == 1
    assert not ActivityBlock.objects.filter(pk=activity_block.id).exists()


@pytest.mark.django_db
def test_bulk_upsert_duplicate_deleted_ids_counted_once(api_client, activity_block):
    """Duplicaten in deleted_ids worden als één verwijdering geteld."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [], "deleted_ids": [activity_block.id, activity_block.id]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["deleted"] == 1
    assert ActivityBlock.objects.count() == 0


# ── API contract: exacte JSON-shape ──────────────────────────────────────────

ACTIVITY_BLOCK_READ_FIELDS = {
    "id", "app_name", "date", "started_at", "ended_at",
    "total_seconds", "total_minutes", "activity_count", "block_minutes",
    "dominant_title", "project", "project_name", "suggested_projects",
    "unique_activities",
}
# project_id is write-only — mag niet in de response zitten
WRITE_ONLY_FIELDS = {"project_id"}


@pytest.mark.django_db
def test_activity_block_detail_has_all_expected_fields(api_client, activity_block):
    """Detail-response bevat precies de velden die de frontend verwacht."""
    response = api_client.get(f"/api/activities/activity-blocks/{activity_block.id}/")
    assert response.status_code == 200
    actual = set(response.data.keys())
    missing = ACTIVITY_BLOCK_READ_FIELDS - actual
    extra   = actual - ACTIVITY_BLOCK_READ_FIELDS
    assert not missing, f"velden ontbreken in response: {missing}"
    assert not extra,   f"onverwachte velden in response: {extra}"


@pytest.mark.django_db
def test_activity_block_detail_write_only_fields_absent(api_client, activity_block):
    """Write-only velden (project_id) zijn niet zichtbaar in de response."""
    response = api_client.get(f"/api/activities/activity-blocks/{activity_block.id}/")
    assert response.status_code == 200
    for field in WRITE_ONLY_FIELDS:
        assert field not in response.data, f"write-only veld '{field}' zit ten onrechte in de response"


@pytest.mark.django_db
def test_activity_block_detail_field_types(api_client, activity_block):
    """Veldtypen kloppen met wat de frontend verwacht."""
    response = api_client.get(f"/api/activities/activity-blocks/{activity_block.id}/")
    d = response.data
    checks = [
        ("id",               int),
        ("app_name",         str),
        ("total_seconds",    int),
        ("total_minutes",    float),
        ("activity_count",   int),
        ("block_minutes",    int),
        ("unique_activities", list),
        ("suggested_projects", list),
    ]
    for field, expected_type in checks:
        assert isinstance(d[field], expected_type), (
            f"'{field}': verwacht {expected_type.__name__}, kreeg {type(d[field]).__name__} ({d[field]!r})"
        )
    assert d["project"] is None, f"'project': verwacht null, kreeg {d['project']!r}"


@pytest.mark.django_db
def test_activity_block_list_pagination_envelope(api_client):
    """Lijstresponse gebruikt de standaard DRF-paginering: count + results."""
    response = api_client.get("/api/activities/activity-blocks/")
    assert response.status_code == 200
    assert "count"   in response.data
    assert "results" in response.data
    assert isinstance(response.data["count"],   int)
    assert isinstance(response.data["results"], list)


@pytest.mark.django_db
def test_activity_block_list_result_has_all_fields(api_client, activity_block):
    """Elk item in de lijst bevat dezelfde velden als de detail-response."""
    response = api_client.get(f"/api/activities/activity-blocks/?date={activity_block.date}")
    assert response.status_code == 200
    item = response.data["results"][0]
    assert set(item.keys()) == ACTIVITY_BLOCK_READ_FIELDS


@pytest.mark.django_db
def test_activity_block_project_inline_has_exact_fields(api_client, activity_block_with_project):
    """Genest project-object bevat precies {id, name, color} — niet meer, niet minder."""
    response = api_client.get(f"/api/activities/activity-blocks/{activity_block_with_project.id}/")
    assert response.status_code == 200
    assert set(response.data["project"].keys()) == {"id", "name", "color"}


@pytest.mark.django_db
def test_bulk_response_blocks_have_all_fields(api_client):
    """blocks-array in de bulk-response bevat volledige blokobjecten."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": [{"started_at": "2026-03-13T09:00:00Z", "total_seconds": 900}]},
        format="json",
    )
    assert response.status_code == 200
    item = response.data["blocks"][0]
    assert set(item.keys()) == ACTIVITY_BLOCK_READ_FIELDS


@pytest.mark.django_db
def test_bulk_response_envelope_has_exact_keys(api_client):
    """Bulk-response heeft precies {created, updated, deleted, blocks}."""
    response = api_client.post(
        "/api/activities/activity-blocks/bulk/",
        {"blocks": []},
        format="json",
    )
    assert response.status_code == 200
    assert set(response.data.keys()) == {"created", "updated", "deleted", "blocks"}