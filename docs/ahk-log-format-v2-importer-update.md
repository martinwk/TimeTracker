# Task: update the time-log importer for the new log format (keep old format working)

> Saved 2026-07-16. Referenced from the "Key TODO" list in [CLAUDE.md](../CLAUDE.md).
> Not implemented yet — this file is the spec for when the work is picked up.

The AutoHotkey window tracker writes monthly log files (`window_log_YYYY-MM.txt`,
UTF-8, possibly with BOM, LF or CRLF line endings). On 2026-07-16 the format
changed **mid-file**, so format detection must happen **per line, not per file**.

## Line types

### 1. Old segment line (before 2026-07-16) — 3 fields, 2 pipes
```
2026-03-13 09:14:00 - 2026-03-13 09:14:06 | 000 min | track_window_log.ahk - AutoHotkey - Visual Studio Code
```
`start - end | duration | title`. Split on the **first 2 pipes only**: the title
may itself contain `|`. Special titles: `Idle`, `Desktop`, `Untitled`.

### 2. New segment line — 5 fields, 4 pipes
```
2026-07-16 14:02:11 - 2026-07-16 14:09:45 | 007 min | chrome.exe | https://example.com/page | Example page - Google Chrome
```
`start - end | duration | process | detail | title`. Split on the **first 4
pipes only**: the title may contain `|` (the detail field is sanitized by the
tracker, `|` → `/`, so it never contains pipes).

- **process**: exe name (`chrome.exe`), a package name (`MSTeams`), or empty.
  Original casing is preserved (`WINWORD.EXE`, `Notepad.exe`) — always compare
  case-insensitively.
- **detail** (URL, file path, mail subject or appointment — see below): only
  available for apps the tracker has a handler for; it is often empty. The
  **title** (last field) is the only field guaranteed to be present on every
  segment line, so title-based classification must always work as a fallback
  when detail is empty. Meaning of detail depends on context (trim all fields):
  - browsers → URL of the active tab (captured once at segment start)
  - `outlook.exe` → subject of the selected mail
  - Word/Excel/PowerPoint/Explorer → full document/folder path; for documents
    opened from SharePoint/OneDrive this is a URL, not a local path
  - title `InCall` → subject of the currently running Outlook calendar appointment
  - title `Idle` → window title of the foreground window during the idle period
  - all other apps → empty
- **title** special values (last field):
  - `Idle` — no input >60s, screen unlocked. Process + foreground title are
    preserved in fields 3/4: idle time in a reading app (Zotero, PDF viewer,
    browser) most likely means reading, not a break. Reading sessions appear as
    alternating short active segments and Idle segments of the same process —
    consider merging those into one block.
  - `InCall` — no input but the microphone is live: a call/meeting. Process =
    the app holding the mic. Billable; use detail (appointment subject) to
    assign it to a project.
  - `Locked` — session locked: definitely away, never billable.
  - `Desktop`, `Untitled` — as before.

### 3. MARK line (new) — manual project tag, 2 pipes, no end timestamp
```
2026-07-16 14:30:00 | MARK | ProjectX
```
Ground truth from the user: attribute segments **after** this timestamp to the
given project, overriding rule-based classification. **Scope: a MARK is valid
until the next MARK or until the end of that calendar day, whichever comes
first. Marks never carry over to the next day — every day starts unmarked.**

## Per-line detection algorithm
1. Field between the 1st and 2nd pipe equals `MARK` → MARK line.
2. First field contains ` - ` (two timestamps) → segment line:
   - ≥4 pipes **and** the would-be process field (3rd) contains no spaces →
     parse as new format;
   - otherwise → old format (covers rare old titles containing `|`).
3. Anything else → skip, but log a warning.

## Other rules
- Never trust the `NNN min` field (floored to whole minutes); always recompute
  duration from the two timestamps. Keep doing this.
- Match process names case-insensitively everywhere (the tracker logs the
  process name exactly as Windows reports it, so casing varies).
- Old-format `Idle` semantics: the ~60s before each idle segment were
  attributed to the previous window. New-format boundaries are exact
  (backdated by the tracker). Optionally correct old data for this.
- Existing filtering/aggregation must keep working unchanged on old files.
- Add tests with mixed-format files: old lines, new lines, MARK lines, titles
  containing pipes, empty detail/process fields, and process names in
  varying case.
- Add this item to the project TODO list (do not implement it now):
  "When building project-mapping rules, match on the detail field (file paths
  and URLs) in preference to the window title — titles only show base names
  and are ambiguous; paths and URLs are stable project identifiers. The title
  is always present and is the fallback for apps without detail."

---

## Assessment (2026-07-16): does the current importer break on new-format lines?

No crash, but **silent data corruption** on any new-format line already parsed
by the current [`importer.py`](../backend/apps/activities/importer.py):

- `LINE_RE` only requires `start - end | NNN min | <rest>` and captures
  everything after the 2nd pipe as `raw_title` — it has no opinion on further
  `|` characters. A new-format segment line therefore parses "successfully",
  but `raw_title` ends up as `process | detail | title` concatenated
  (e.g. `"notepad.exe |  | Idle"`), not the bare title.
- `detect_noise()` (`models.py`) compares `raw_title.strip().lower()` against
  `NOISE_TITLES` (`"idle"`, `"program manager"`, …) for an **exact** match.
  A new-format `Idle`/`Desktop`/`Untitled` line no longer matches exactly, so
  it is **not** flagged `is_noise` — idle time silently starts counting as
  active time.
- `extract_app_name()` looks for the last `" - "`/`" — "` separator in
  `raw_title`. With the process/detail prefix present, this sometimes still
  resolves correctly by luck (browser titles already end in `" - Chrome"`),
  but for anything without such a separator in the title portion, the whole
  concatenated string becomes the "app name".
- MARK lines (`timestamp | MARK | Project`) have only one timestamp, so
  `LINE_RE` never matches them. `parse_line()` returns `None` for any
  non-matching line with **no logging at all** — MARK lines are dropped
  without a trace, not just skipped-with-a-warning as the spec above intends.

Net effect: the importer does not fail or refuse new-format files, but every
sync since the AHK update on 2026-07-16 has likely been quietly mislabeling
idle time as active and mangling `app_name` for new-format segments. This is
not a hard failure, so it doesn't block using the app, but it does mean
existing time totals since the format change should be treated with suspicion
until this is implemented. See the TODO list in
[CLAUDE.md](../CLAUDE.md#current-state) for the follow-up items.
