# TimeTracker

> **Maintenance:** Keep this file and `README.md` up to date. When design choices, architecture, data flow, models, features, or the current state of the project change, update the relevant sections in both files before ending the session.

## What this is

A personal time tracking tool that imports AutoHotkey (AHK) window activity logs, aggregates them into meaningful time blocks, and lets you assign those blocks to projects via a visual timeline. The goal is low-friction time tracking: AHK runs in the background logging what you work on, and TimeTracker turns that raw log into billable/reportable time.

**Language:** UI text and model labels are in Dutch. Timezone: Europe/Amsterdam. Locale: nl-nl.

---

## Architecture

Monorepo: Django REST API backend + Vue 3 SPA frontend.

```
TimeTracker/
├── backend/          # Django 4.2 + DRF
│   ├── config/       # settings, urls, wsgi
│   └── apps/
│       ├── activities/   # core domain: window logs, blocks, rules
│       └── projects/     # projects and time entries
└── frontend/         # Vue 3 + Vite + Pinia + Tailwind CSS 4
    └── src/
        ├── views/        # Dashboard, Projects, Stats pages
        ├── components/   # ActivityBlockGrid, ActivityBlock, etc.
        ├── stores/       # activityBlocks.js (central Pinia store)
        └── api/          # Axios client (base URL: http://localhost:8000/api)
```

---

## Data flow

```
AHK window log (text file)
  → POST /api/activities/import/
  → WindowActivity records (raw, immutable)
  → Aggregator groups consecutive same-app activities into ActivityBlocks
  → ActivityBlocks displayed on timeline (unassigned = gray)
  → User assigns blocks to Projects (manually or via ActivityRules)
  → BlockProjectHistory records every assignment for audit
```

---

## Core models

| Model | Purpose |
|---|---|
| `WindowActivity` | Raw AHK log line. Never modified after import. |
| `ActivityBlock` | Aggregated block (consecutive activities, same app). Has optional FK to Project. |
| `UniqueActivity` | Distinct window titles within a block, ordered by duration. |
| `ActivityRule` | Pattern-based auto-assignment. Matched by priority (lower = first). |
| `Project` | Target project. Has `color` (hex) for timeline rendering. |
| `BlockProjectHistory` | Audit trail: which project, when, by rule or manual. |

---

## Design decisions

**Immutable import:** WindowActivity records are never touched after import. Aggregation creates derived records (ActivityBlock, UniqueActivity) that can be regenerated without data loss.

**Priority-based rules:** First matching rule wins. No multi-rule stacking. History tracked for debugging.

**Noise filtering:** Idle, Program Manager, Task Switching are flagged `is_noise=True` and hidden from the UI, but kept in the database.

**App name extraction:** Heuristic — tries "Document - AppName" or "Page — Firefox" separators, falls back to full title. Enables grouping by app despite varying window titles.

**Visual merging:** Adjacent blocks with the same project merge visually in `mergedBlocksByDay` (computed property in Pinia store). Selection and mutations still operate on individual blocks.

**UTC storage, local display:** All timestamps stored UTC in Django. Frontend converts to Europe/Amsterdam for display.

---

## Current state

Backend is complete (models, importer, aggregator, rule engine, DRF API). Frontend store is fully wired to the live API — mock data (`makeMockBlocks()`) is still present for reference but no longer used in production flows.

**API contract (ActivityBlock):**
- `GET /api/activity-blocks/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — fetch week
- `POST /api/activity-blocks/` — create block (requires `started_at`, `total_seconds`; optional `project_id`)
- `PATCH /api/activity-blocks/{id}/` — update block; `ended_at` and `date` auto-recalculated from `started_at + total_seconds`
- `POST /api/activity-blocks/assign/` — bulk assign: `{ block_ids: [...], project_id: N|null }`
- `POST /api/activity-blocks/bulk/` — bulk upsert + delete: `{ blocks: [{id?, started_at, total_seconds, project_id?}], deleted_ids?: [...] }` → `{ created, updated, deleted, blocks }`
- `GET /api/projects/` — list projects
- `POST /api/activities/apply-rules/` — run rules engine: `{ date_from, date_to }`

**Serializer:** `project` is a nested read-only object `{ id, name, color }`; write via `project_id` (write-only FK field).

**Test coverage:** 138 backend tests (pytest), 64 frontend tests (Vitest).

**Bulk endpoint — ID-onderscheid:** Temp-IDs (aangemaakt in de frontend met `Date.now() * 1000 + m`) zijn > 1e12. Echte backend-IDs zijn < 1e12. De frontend stuurt alleen echte IDs mee in `deleted_ids`.

Key TODO:
- Projects view (CRUD)
- Stats view
- Remove `makeMockBlocks()` mock data

---

## Development guidelines

**Test-driven development:** All new functionality must be developed test-first (TDD) unless explicitly told otherwise. Write a failing test, make it pass, then refactor. This applies to both backend (pytest) and frontend (Vitest).

**Commit messages:** Always write in English.

## Terminal

Use **Git Bash** (not PowerShell or cmd) for all shell commands in this project.

## Running the project

**Backend:**
```bash
cd backend
source .venv/Scripts/activate
python manage.py runserver
```

**Frontend:**
```bash
cd frontend
npm run dev
```

Frontend dev server proxies to `http://localhost:8000`. Both must run simultaneously.

**Tests (backend):**
```bash
cd backend
pytest
```

---

## Key files

- [backend/apps/activities/models.py](backend/apps/activities/models.py) — core data models
- [backend/apps/activities/importer.py](backend/apps/activities/importer.py) — AHK log parser
- [backend/apps/activities/aggregator.py](backend/apps/activities/aggregator.py) — block aggregation logic
- [backend/apps/activities/rule_engine.py](backend/apps/activities/rule_engine.py) — auto-assignment rules
- [backend/apps/activities/views.py](backend/apps/activities/views.py) — DRF viewsets
- [frontend/src/stores/activityBlocks.js](frontend/src/stores/activityBlocks.js) — central Pinia store (fully wired to API; mock data still present but unused)
- [frontend/src/components/ActivityBlockGrid.vue](frontend/src/components/ActivityBlockGrid.vue) — interactive timeline grid
- [frontend/src/components/ActivityBlock.vue](frontend/src/components/ActivityBlock.vue) — individual block with resize handles
- [frontend/src/api/api.js](frontend/src/api/api.js) — Axios client setup
