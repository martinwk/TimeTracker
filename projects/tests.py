from datetime import date

import pytest

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
