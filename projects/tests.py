from datetime import date

import pytest
from rest_framework.test import APIClient

from activities.models import WindowActivity
from projects.models import ActivityMapping, Project, TimeEntry


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def project(db):
    return Project.objects.create(name="Onderzoek", color="#4F86C6")


@pytest.fixture
def other_project(db):
    return Project.objects.create(name="Administratie", color="#E8593C")


@pytest.fixture
def time_entry(project):
    return TimeEntry.objects.create(
        project=project,
        date=date(2026, 3, 13),
        duration_minutes=90,
        notes="Literatuurstudie",
    )


@pytest.fixture
def activity(db):
    from datetime import datetime, timezone
    start = datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc)
    end   = datetime(2026, 3, 13, 9, 30, tzinfo=timezone.utc)
    a = WindowActivity.from_log_line(start, end, "Koers zetten - Lockefeer - Zotero")
    a.save()
    return a


# ── Project ───────────────────────────────────────────────────────────────────

def test_project_str(project):
    assert str(project) == "Onderzoek"


def test_project_defaults(project):
    assert project.is_active is True
    assert project.notes == ""


def test_project_total_minutes_no_entries(project):
    assert project.total_minutes() == 0


def test_project_total_minutes_with_entries(project):
    TimeEntry.objects.create(project=project, date=date(2026, 3, 13), duration_minutes=60)
    TimeEntry.objects.create(project=project, date=date(2026, 3, 13), duration_minutes=45)
    assert project.total_minutes() == 105


def test_project_total_minutes_filtered_by_date(project):
    TimeEntry.objects.create(project=project, date=date(2026, 3, 13), duration_minutes=60)
    TimeEntry.objects.create(project=project, date=date(2026, 3, 14), duration_minutes=30)
    assert project.total_minutes(date=date(2026, 3, 13)) == 60
    assert project.total_minutes(date=date(2026, 3, 14)) == 30


def test_project_total_minutes_other_project_not_counted(project, other_project):
    TimeEntry.objects.create(project=project,       date=date(2026, 3, 13), duration_minutes=60)
    TimeEntry.objects.create(project=other_project, date=date(2026, 3, 13), duration_minutes=99)
    assert project.total_minutes() == 60


def test_project_name_unique(project):
    with pytest.raises(Exception):
        Project.objects.create(name="Onderzoek", color="#000000")


# ── TimeEntry ─────────────────────────────────────────────────────────────────

def test_time_entry_str(time_entry):
    assert "Onderzoek" in str(time_entry)
    assert "2026-03-13" in str(time_entry)
    assert "1u 30" in str(time_entry)


def test_time_entry_duration_hours(time_entry):
    assert time_entry.duration_hours == 1.5


def test_time_entry_duration_hours_rounding(project):
    entry = TimeEntry.objects.create(
        project=project,
        date=date(2026, 3, 13),
        duration_minutes=100,
    )
    assert entry.duration_hours == 1.67


def test_time_entry_zero_minutes_not_allowed(project):
    with pytest.raises(Exception):
        entry = TimeEntry(project=project, date=date(2026, 3, 13), duration_minutes=0)
        entry.full_clean()


def test_time_entry_project_protect_on_delete(time_entry, project):
    """Project mag niet verwijderd worden zolang er TimeEntries aan hangen."""
    from django.db.models import ProtectedError
    with pytest.raises(ProtectedError):
        project.delete()


# ── ActivityMapping ───────────────────────────────────────────────────────────

def test_activity_mapping_str(activity, time_entry):
    mapping = ActivityMapping.objects.create(
        activity=activity,
        time_entry=time_entry,
        source=ActivityMapping.SOURCE_RULE,
    )
    assert "Zotero" in str(mapping)
    assert "Onderzoek" in str(mapping)


def test_activity_mapping_source_default(activity, time_entry):
    mapping = ActivityMapping.objects.create(
        activity=activity,
        time_entry=time_entry,
    )
    assert mapping.source == ActivityMapping.SOURCE_RULE


def test_activity_mapping_manual_source(activity, time_entry):
    mapping = ActivityMapping.objects.create(
        activity=activity,
        time_entry=time_entry,
        source=ActivityMapping.SOURCE_MANUAL,
    )
    assert mapping.source == ActivityMapping.SOURCE_MANUAL


def test_activity_mapping_unique_together(activity, time_entry):
    """Dezelfde activiteit mag maar één keer aan dezelfde TimeEntry hangen."""
    ActivityMapping.objects.create(activity=activity, time_entry=time_entry)
    with pytest.raises(Exception):
        ActivityMapping.objects.create(activity=activity, time_entry=time_entry)


def test_activity_mapping_same_activity_different_entries(activity, project):
    """Dezelfde activiteit mag wel aan twee verschillende TimeEntries hangen."""
    entry1 = TimeEntry.objects.create(project=project, date=date(2026, 3, 13), duration_minutes=30)
    entry2 = TimeEntry.objects.create(project=project, date=date(2026, 3, 13), duration_minutes=30)
    ActivityMapping.objects.create(activity=activity, time_entry=entry1)
    ActivityMapping.objects.create(activity=activity, time_entry=entry2)
    assert ActivityMapping.objects.count() == 2


# ── API Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


# ── API: ProjectViewSet ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_project_list(api_client, project):
    """GET /api/projects/ should return all projects."""
    response = api_client.get("/api/projects/")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Onderzoek"


@pytest.mark.django_db
def test_project_detail(api_client, project):
    """GET /api/projects/{id}/ should return single project."""
    response = api_client.get(f"/api/projects/{project.id}/")
    assert response.status_code == 200
    assert response.data["name"] == "Onderzoek"
    assert response.data["is_active"] is True


@pytest.mark.django_db
def test_project_filter_by_is_active(api_client, project):
    """Filter projects by is_active status."""
    response = api_client.get("/api/projects/?is_active=true")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_project_create(api_client):
    """POST to create a new project."""
    data = {
        "name": "New Project",
        "color": "#FF0000",
        "is_active": True,
        "notes": "Test project",
    }
    response = api_client.post("/api/projects/", data)
    assert response.status_code == 201
    assert Project.objects.count() == 1
    assert response.data["name"] == "New Project"


@pytest.mark.django_db
def test_project_update(api_client, project):
    """PATCH to update project."""
    data = {"color": "#FF0000"}
    response = api_client.patch(f"/api/projects/{project.id}/", data)
    assert response.status_code == 200
    project.refresh_from_db()
    assert project.color == "#FF0000"


@pytest.mark.django_db
def test_project_delete(api_client, project):
    """DELETE to remove a project (should fail if has time entries)."""
    response = api_client.delete(f"/api/projects/{project.id}/")
    assert response.status_code == 204
    assert Project.objects.count() == 0


# ── API: TimeEntryViewSet ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_time_entry_list(api_client, time_entry):
    """GET /api/time-entries/ should return all entries."""
    response = api_client.get("/api/time-entries/")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_time_entry_detail(api_client, time_entry):
    """GET /api/time-entries/{id}/ should return entry with computed fields."""
    response = api_client.get(f"/api/time-entries/{time_entry.id}/")
    assert response.status_code == 200
    assert response.data["duration_minutes"] == 90
    assert response.data["duration_hours"] == 1.5
    assert response.data["project_name"] == "Onderzoek"


@pytest.mark.django_db
def test_time_entry_filter_by_project(api_client, time_entry, project):
    """Filter time entries by project."""
    response = api_client.get(f"/api/time-entries/?project={project.id}")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_time_entry_filter_by_date(api_client, time_entry):
    """Filter time entries by date."""
    response = api_client.get("/api/time-entries/?date=2026-03-13")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_time_entry_create(api_client, project):
    """POST to create a new time entry."""
    data = {
        "project": project.id,
        "date": "2026-03-14",
        "duration_minutes": 120,
        "notes": "Development work",
    }
    response = api_client.post("/api/time-entries/", data)
    assert response.status_code == 201
    assert TimeEntry.objects.count() == 1


@pytest.mark.django_db
def test_time_entry_update(api_client, time_entry):
    """PATCH to update time entry."""
    data = {"duration_minutes": 120}
    response = api_client.patch(f"/api/time-entries/{time_entry.id}/", data)
    assert response.status_code == 200
    time_entry.refresh_from_db()
    assert time_entry.duration_minutes == 120


# ── API: ActivityMappingViewSet ────────────────────────────────────────────────

@pytest.mark.django_db
def test_activity_mapping_list(api_client, activity, time_entry):
    """GET /api/activity-mappings/ should return all mappings."""
    mapping = ActivityMapping.objects.create(
        activity=activity,
        time_entry=time_entry,
        source=ActivityMapping.SOURCE_RULE,
    )
    response = api_client.get("/api/activity-mappings/")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_activity_mapping_detail(api_client, activity, time_entry):
    """GET /api/activity-mappings/{id}/ should return mapping with nested info."""
    mapping = ActivityMapping.objects.create(
        activity=activity,
        time_entry=time_entry,
        source=ActivityMapping.SOURCE_RULE,
    )
    response = api_client.get(f"/api/activity-mappings/{mapping.id}/")
    assert response.status_code == 200
    assert response.data["activity_app"] == "Zotero"
    assert response.data["time_entry_project"] == "Onderzoek"
    assert response.data["source_display"] == "Automatisch (regel)"


@pytest.mark.django_db
def test_activity_mapping_filter_by_source(api_client, activity, time_entry):
    """Filter mappings by source."""
    ActivityMapping.objects.create(
        activity=activity,
        time_entry=time_entry,
        source=ActivityMapping.SOURCE_RULE,
    )
    response = api_client.get(f"/api/activity-mappings/?source={ActivityMapping.SOURCE_RULE}")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_activity_mapping_create(api_client, activity, time_entry):
    """POST to create a new activity mapping."""
    data = {
        "activity": activity.id,
        "time_entry": time_entry.id,
        "source": ActivityMapping.SOURCE_MANUAL,
    }
    response = api_client.post("/api/activity-mappings/", data)
    assert response.status_code == 201
    assert ActivityMapping.objects.count() == 1


@pytest.mark.django_db
def test_activity_mapping_create_duplicate_fails(api_client, activity, time_entry):
    """Creating duplicate mapping should fail."""
    ActivityMapping.objects.create(activity=activity, time_entry=time_entry)
    data = {
        "activity": activity.id,
        "time_entry": time_entry.id,
        "source": ActivityMapping.SOURCE_MANUAL,
    }
    response = api_client.post("/api/activity-mappings/", data)
    # Should fail with 400 Bad Request due to unique_together constraint
    assert response.status_code == 400
