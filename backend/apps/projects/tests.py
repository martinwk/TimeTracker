"""
Tests for the projects app.
Updated for Phase 3: focuses on Project model with ActivityBlock integration.
"""

from datetime import date, datetime, timezone

import pytest
from rest_framework.test import APIClient

from apps.activities.models import ActivityBlock, WindowActivity
from apps.projects.models import Project


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def project(db):
    return Project.objects.create(name="Onderzoek", color="#4F86C6")


@pytest.fixture
def other_project(db):
    return Project.objects.create(name="Administratie", color="#E8593C")


@pytest.fixture
def activity_block(db, project):
    """Create an ActivityBlock assigned to a project."""
    return ActivityBlock.objects.create(
        app_name="Zotero",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=project,
    )


# ── Project Model Tests ────────────────────────────────────────────────────────

def test_project_str(project):
    assert str(project) == "Onderzoek"


def test_project_defaults(project):
    assert project.is_active is True
    assert project.notes == ""


def test_project_total_minutes_no_blocks(project):
    """Project with no blocks should have 0 minutes."""
    assert project.total_minutes() == 0


def test_project_total_minutes_with_blocks(project):
    """Project total_minutes should aggregate ActivityBlock durations."""
    ActivityBlock.objects.create(
        app_name="VSCode",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,  # 1 hour
        activity_count=1,
        block_minutes=15,
        project=project,
    )
    ActivityBlock.objects.create(
        app_name="Word",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 45, tzinfo=timezone.utc),
        total_seconds=2700,  # 45 minutes
        activity_count=1,
        block_minutes=15,
        project=project,
    )
    assert project.total_minutes() == 105.0  # 60 + 45 = 105 minutes


def test_project_total_minutes_filtered_by_date(project):
    """Project total_minutes should filter by date."""
    ActivityBlock.objects.create(
        app_name="VSCode",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=project,
    )
    ActivityBlock.objects.create(
        app_name="Word",
        date=date(2026, 3, 14),
        started_at=datetime(2026, 3, 14, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 14, 9, 30, tzinfo=timezone.utc),
        total_seconds=1800,
        activity_count=1,
        block_minutes=15,
        project=project,
    )
    assert project.total_minutes(date=date(2026, 3, 13)) == 60.0
    assert project.total_minutes(date=date(2026, 3, 14)) == 30.0


def test_project_total_minutes_other_project_not_counted(project, other_project):
    """Project total_minutes should not count blocks from other projects."""
    ActivityBlock.objects.create(
        app_name="VSCode",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        total_seconds=3600,
        activity_count=1,
        block_minutes=15,
        project=project,
    )
    ActivityBlock.objects.create(
        app_name="Word",
        date=date(2026, 3, 13),
        started_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 13, 11, 39, tzinfo=timezone.utc),
        total_seconds=5940,
        activity_count=1,
        block_minutes=15,
        project=other_project,
    )
    assert project.total_minutes() == 60.0
    assert other_project.total_minutes() == 99.0


def test_project_name_unique(project):
    """Project names should be unique."""
    with pytest.raises(Exception):
        Project.objects.create(name="Onderzoek", color="#000000")


# ── API: ProjectViewSet ────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


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
    """DELETE to remove a project (should work if no activity blocks)."""
    response = api_client.delete(f"/api/projects/{project.id}/")
    assert response.status_code == 204
    assert Project.objects.count() == 0

