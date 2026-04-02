from datetime import datetime, timezone

import pytest
from rest_framework.test import APIClient

from activities.models import WindowActivity, ActivityBlock, UniqueActivity, ActivityRule, detect_noise, extract_app_name


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
    from projects.models import Project
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