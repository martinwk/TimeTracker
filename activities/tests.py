from datetime import datetime, timezone

import pytest

from activities.models import WindowActivity, detect_noise, extract_app_name


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