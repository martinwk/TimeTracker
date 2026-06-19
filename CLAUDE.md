# TimeTracker

> **Maintenance:** Keep this file and `README.md` up to date. When design choices, architecture, data flow, models, features, or the current state of the project change, update the relevant sections in both files before ending the session.

## What this is

A personal time tracking tool that imports AutoHotkey (AHK) window activity logs, aggregates them into meaningful time blocks, and lets you assign those blocks to projects via a visual timeline. The goal is low-friction time tracking: AHK runs in the background logging what you work on, and TimeTracker turns that raw log into billable/reportable time.

**Language:** UI text and model labels are in Dutch. Timezone: Europe/Amsterdam. Locale: nl-nl.

---

## Architecture

Monorepo: Django REST API backend + Vue 3 SPA frontend.

```text
TimeTracker/
├── backend/          # Django 4.2 + DRF
│   ├── config/       # settings, urls, wsgi
│   └── apps/
│       ├── activities/   # core domain: window logs, blocks, rules
│       └── projects/     # projects and time entries
└── frontend/         # Vue 3 + Vite + Pinia + Tailwind CSS 4
    └── src/
        ├── views/        # Dashboard, Projects, Weekstaat, Stats pages
        ├── components/   # ActivityBlockGrid, ActivityBlock, etc.
        ├── stores/       # activityBlocks.js (central Pinia store)
        └── api/          # Axios client (base URL: http://localhost:8000/api)
```

---

## Data flow

```text
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
| --- | --- |
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

**Visual merging:** Adjacent blocks with the same project merge visually in `mergedBlocksByDay` (computed property in Pinia store). Selection and mutations still operate on individual blocks. `blocksByDay` no longer exists as a separate computed — it's inlined.

**Resize/move via primitives (ontwerp B):** The grid passes only primitive values to store actions — never object references. `resizeRange(iso, oldStartMin, oldEndMin, newStartMin, newEndMin, projectId)` and `moveBlocks(blockIds, targetIso, deltaMin)` look up the blocks themselves. This avoids stale references to computed outputs. The grid's `window` mousemove listener must NOT be blocked by `.stop` on child element events — `ActivityBlock` uses `@mousemove` (no `.stop`) for this reason.

**UTC storage, local display:** All timestamps stored UTC in Django. Frontend converts to Europe/Amsterdam for display.

**Click on assigned block shows reassignment popup:** Clicking an assigned block (without dragging) opens the `SlotSuggestion` popup with title "Opnieuw toewijzen". Activities are fetched via `getTopActivitiesForIds(blockIds)` — unlike `getTopActivities` which only considers unassigned aggregator blocks, this looks up `unique_activities` by block ID regardless of assignment status. `assignToProject` accepts `null` to unassign (backend `assign/` endpoint also accepts `project_id: null`). Closing any popup (Escape, outside click, Annuleren) clears the selection, which dismisses the toolbar buttons "Wis selectie" and "Toewijzen aan project".

**Aggregatie is destructief — handmatige toewijzingen overleven herberekening (Optie C, geïmplementeerd):** `aggregate_day()` snapshottert vóór delete alle handmatige toewijzingen (`assigned_by='manual'`) als `{started_at → project_id}`. Na herberekening worden die toewijzingen hersteld op nieuwe blokken met dezelfde `started_at`. Rule-toewijzingen worden niet hersteld — de engine herevalueert die.

**BlockProjectHistory-gat in assign-endpoint (gerepareerd):** De assign-endpoint maakt nu een `BlockProjectHistory`-record aan met `assigned_by='manual'` voor elk toegewezen blok.

**Rule engine beschermt handmatige toewijzingen (geïmplementeerd):** De rule engine gebruikt een `Exists`-subquery om blokken met een `assigned_by='manual'` history-entry uit te sluiten. Blokken met alleen `assigned_by='rule'` history worden wél opnieuw geëvalueerd, zodat regelwijzigingen doorwerken op eerder automatisch toegewezen blokken. Idempotent: als de regel hetzelfde project zou toewijzen, wordt geen nieuwe history-entry aangemaakt.

**Sync-workflow (geïmplementeerd):** De frontend biedt een sync-knop (cirkelende pijlen linksonder in de sidebar) die `POST /api/activities/sync/` aanroept. De backend importeert het AHK-logbestand (auto-detect: `{AHK_LOG_DIR}/window_log_{YYYY-MM}.txt`) en herberekent alle dagen die in het logbestand voorkomen — ook al-geaggregeerde dagen, zodat nieuwe log-entries worden meegenomen. Optie C beschermt handmatige toewijzingen. Bij succes toont de knop kort de resultaten (X blokken, Y dagen); bij een ontbrekend logbestand verschijnt een foutmelding. Overige instellingen (logbestandpad, fallback filepicker, regels toepassen) zijn nog niet geïmplementeerd (cogwheel-menu).

**Hover tooltip toont activiteiten voor zowel ongeassigneerde als toegewezen blokken:** `onColumnMouseMove` in `ActivityBlockGrid` detecteert via `e.target.closest('.activity-block')` of de cursor over een interactief blok beweegt. Zo ja: lees `data-group-key` (= eerste block-ID van de merged group), zoek de groep op in `mergedBlocksByDay`, en toon `getTopActivitiesForIds(group.blocks.map(b => b.id))` — de cumulatieve activiteitenlijst over alle blokken in de groep. Zo nee: toon `getTopActivities` voor het 15-min slot (alleen ongeassigneerde aggregator-blokken).

---

## Current state

Backend is complete (models, importer, aggregator, rule engine, DRF API). Frontend is fully wired to the API — mock data has been removed. The full drag interaction layer (resize, move, drag-select, project assign) works and persists to the backend.

**API contract (ActivityBlock):**

- `GET /api/activity-blocks/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — fetch week
- `POST /api/activity-blocks/` — create block (requires `started_at`, `total_seconds`; optional `project_id`)
- `PATCH /api/activity-blocks/{id}/` — update block; `ended_at` and `date` auto-recalculated from `started_at + total_seconds`
- `POST /api/activity-blocks/assign/` — bulk assign: `{ block_ids: [...], project_id: N|null }`
- `POST /api/activity-blocks/bulk/` — bulk upsert + delete: `{ blocks: [{id?, started_at, total_seconds, project_id?}], deleted_ids?: [...] }` → `{ created, updated, deleted, blocks }`
- `GET /api/projects/` — list projects
- `POST /api/activities/apply-rules/` — run rules engine: `{ date_from, date_to }`
- `POST /api/activities/sync/` — import logbestand + herbereken alle dagen in het logbestand: `{}` of `{ "log_path": "/override" }` → `{ log_file, imported, days_aggregated: [...], blocks_created }`

**Serializer:** `project` is a nested read-only object `{ id, name, color }`; write via `project_id` (write-only FK field).

**Test coverage:** 164 backend tests (pytest), 223 frontend tests (Vitest).

**Bulk endpoint — ID-onderscheid:** Temp-IDs (aangemaakt in de frontend met `Date.now() * 1000 + m`) zijn > 1e12. Echte backend-IDs zijn < 1e12. De frontend stuurt alleen echte IDs mee in `deleted_ids`.

Key TODO:

- ~~**BUG: Activiteitsduur onjuist bij blok dat kwartiergrens overschrijdt.**~~ Opgelost in commit 652a1a6: `ActivityBlock.vue` gebruikt `visualDurationMin * 60` (gebaseerd op `ended_at`, altijd 15 min per aggregator-blok) in plaats van `totalSeconds` (per-slot overlap-seconden). Backend- en frontendtests toegevoegd die de correcte per-slot overlap bevestigen. Handmatig geverifieerd.
- Stats view (Weekstaat en Projects zijn klaar)
- ~~**Weekstaat: round to quarter-hours.**~~ Opgelost: matrix en weekTotaal gebruiken nu `blockWallClockSeconds` (ended_at − started_at) i.p.v. `total_seconds`, zodat aggregator-blokken altijd als volledige 15-min slots tellen.
- **Investigate: hours total mismatch.** A block that visually spans 1.5 h showed as 16 separate quarter-blocks in the Dashboard and reported 4 h in Weekstaat. Likely caused by stale/duplicate blocks from earlier frontend versions that sent temp-IDs to the assign endpoint (now fixed). Worth adding a management command that compares the sum of `total_seconds` within a contiguous assigned group against the group's wall-clock span, and flags groups where they diverge significantly.
- ~~**Fix: assign-endpoint moet BlockProjectHistory aanmaken.**~~ Geïmplementeerd: `POST /api/activity-blocks/assign/` maakt nu een `BlockProjectHistory`-record aan met `assigned_by='manual'` voor elk toegewezen blok (niet bij ontkoppelen).
- ~~**Implement Optie C: handmatige toewijzingen overleven herberekening.**~~ Geïmplementeerd in `aggregate_day()`.
- **Frontend: beheerpagina voor auto-assign regels.** De backend-API voor `ActivityRule` bestaat al (`GET/POST/PATCH/DELETE /api/activities/activity-rules/`). Er is nog geen frontend-pagina om regels aan te maken, te bewerken en te verwijderen. Een regel heeft: `name`, `match_field` (app_name / dominant_activity / title_contains), `match_value`, `project`, en `priority` (lager = hogere prioriteit). De pagina moet ook een knop bevatten om de rule engine handmatig te draaien voor het huidige weekbereik.
- ~~**Rule engine: handmatig toegewezen blokken niet overschrijven.**~~ Geïmplementeerd: `Exists`-subquery sluit blokken met `assigned_by='manual'` in history uit. Rule-toegewezen blokken worden wél opnieuw geëvalueerd. Handmatig geverifieerd in de frontend.
- ~~**Nieuw endpoint `POST /api/activities/sync/`.**~~ Geïmplementeerd. Importeert en herberekent alle dagen in het logbestand; Optie C beschermt handmatige toewijzingen.
- ~~**Frontend: sync-knop (cirkelende pijlen).**~~ Geïmplementeerd: linksonder in de sidebar, toont resultaten na sync, foutmelding bij ontbrekend logbestand.
- **Frontend: cogwheel-instellingenpaneel.** Bevat: (1) logbestandpad instellen (`AHK_LOG_DIR`); (2) fallback filepicker als auto-detect mislukt (upload via `POST /api/activities/import/`); (3) knop "Regels opnieuw toepassen" (`POST /api/activities/apply-rules/` voor huidig weekbereik).
- **Verwacht gedrag: top-drie telt niet op tot 15 min.** Een blok beslaat altijd een vol 15-min slot op de grid, maar `total_seconds` en de `unique_activities` tonen alleen de werkelijk *actieve* (niet-ruis) tijd. Als het slot grotendeels idle was, kan de top drie 1+0+0 min tonen terwijl het blok visueel 15 min groot is — dat is correct. Eventuele verbetering: toon in de UI expliciet het onderscheid tussen wandkloktijd (blokduur) en actieve tijd (total_seconds).
- ~~**BUG: Verkleind blok laat vrijgekomen slot niet zien als unassigned.**~~ Opgelost: vrijgekomen aggregator-blokken worden nu ontkoppeld (project=null) en in de store gehouden in plaats van verwijderd, zodat ze direct als grijs unassigned blok verschijnen.
- ~~**BUG: Ontkoppeld blok wordt na sync opnieuw toegewezen.**~~ Opgelost: unassign slaat een null-project `BlockProjectHistory`-record op (`assigned_by='manual'`); de aggregator herstelt dit na heraggregatie zodat de rule engine het blok overslaat. Tevens opgelost: de manual_snapshot query ordent nu ascending op `assigned_at` zodat een latere unassign altijd wint van een eerdere toewijzing.
- ~~**Dashboard: gedeclareerde uren per dag zichtbaar.**~~ Geïmplementeerd: `declaredSecondsByDay` in de store telt wandkloktijd van toegewezen blokken per dag; zichtbaar in de dag-headers van het dashboard.
- **Commentaar op toegewezen blok.** Voeg een optioneel tekstveld `comment` toe aan `ActivityBlock`. De gebruiker kan per blok een korte notitie invoeren (bijv. taakomschrijving of facturatienoot). Tonen in het toegewezen blok op de grid en bewerkbaar via de toewijzingspopup.
- **Projectnummers, subnummers en activiteitennummers.** Breid het `Project`-model uit met: `number` (bijv. `2024-042`), `sub_number` (optioneel), `activity_number` (optioneel), `title` (bestaand `name`-veld hernoemen of als alias bijhouden) en `alias` (korte alternatieve naam). Dit maakt het mogelijk om te declareren conform externe projectadministratie (bijv. urenregistratiesysteem van opdrachtgever).
- **Zoeken op project bij bloktoewijzing.** In de `SlotSuggestion`-popup en `ProjectSelector`-modal een zoekbalk toevoegen waarmee de gebruiker kan filteren op projectnaam, nummer of alias. Zoekopdracht werkt client-side op de reeds geladen projectenlijst.
- **"Nieuw project"-knop in toewijzingspopup.** Voeg onderaan de projectkeuzelijst in de `SlotSuggestion`-popup / `ProjectSelector`-modal een knop toe "＋ Nieuw project aanmaken". Klikken opent een inline formulier (naam, kleur, optioneel nummer) en slaat het direct op via `POST /api/projects/`. Het nieuwe project verschijnt direct in de keuzelijst en wordt geselecteerd.

---

## Development guidelines

**Test-driven development:** All new functionality must be developed test-first (TDD) unless explicitly told otherwise. Write a failing test, make it pass, then refactor. This applies to both backend (pytest) and frontend (Vitest).

**Commit messages:** Always write in English.

**Pre-commit quality check:** Before every commit, analyse all changes since the previous commit (`git diff HEAD`) and perform two assessments:

1. **Code quality** — review each changed function/method/module on:
   - *Readability:* are names, structure and logic immediately understandable without extra explanation?
   - *Simplicity:* is there unnecessary complexity, duplication or over-engineering?
   - *Robustness:* are error cases, edge cases and invalid input handled correctly?
   - *Consistency:* does the code match the style and conventions of the rest of the codebase?

   Per finding: file + line number, what the problem is, and a concrete improvement proposal.

2. **Test coverage** — for each changed function/method, verify that a corresponding test exists that:
   - verifies the expected happy-path behaviour
   - covers at least one relevant edge case or error path
   - is descriptive enough to serve as documentation (clear test name, arrange/act/assert structure)

   Per missing or insufficient test: what should be tested and why.

Conclude with a summary: how many changes are qualitatively sound, how many need attention, and what is the most important action to pick up now.

**If any findings are reported (missing tests or quality issues): do not commit. Present the findings and explicitly ask what to do with each issue before proceeding.**

**Commit approval required:** After the quality check, always present the findings to the user and explicitly ask for approval before executing the commit. Never commit autonomously, even when all findings are sound.

**Linter and IDE warnings:** When the IDE reports warnings (Sourcery, markdownlint, etc.) on files touched by a change, address them in the same commit if they are relevant to the changed code. Do not dismiss them as "pre-existing" without fixing them.

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

Backend tests live in:

- `backend/apps/activities/tests.py` — API/view tests for activities
- `backend/apps/activities/test_aggregator.py` — aggregator logic
- `backend/apps/activities/test_importer.py` — AHK log importer
- `backend/apps/activities/test_rule_engine.py` — rule engine
- `backend/apps/projects/tests.py` — API/view tests for projects

Frontend tests (Vitest) live next to their source files:

- `frontend/src/stores/activityBlocks.test.js` — store state & mutations
- `frontend/src/stores/activityBlocks.logic.test.js` — computed/logic
- `frontend/src/stores/activityBlocks.api.test.js` — API integration
- `frontend/src/stores/projects.test.js` — projects store
- `frontend/src/components/ActivityBlock.test.js` — ActivityBlock component
- `frontend/src/components/SlotSuggestion.test.js` — SlotSuggestion popup (keyboard handling)
- `frontend/src/components/ProjectSelector.test.js` — ProjectSelector modal (keyboard handling)
- `frontend/src/views/Projects.test.js` — Projects view
- `frontend/src/views/Weekstaat.test.js` — Weekstaat view
- `frontend/src/utils/date.test.js` — date utilities

---

## Key files

- [backend/apps/activities/models.py](backend/apps/activities/models.py) — core data models
- [backend/apps/activities/importer.py](backend/apps/activities/importer.py) — AHK log parser
- [backend/apps/activities/aggregator.py](backend/apps/activities/aggregator.py) — block aggregation logic
- [backend/apps/activities/rule_engine.py](backend/apps/activities/rule_engine.py) — auto-assignment rules
- [backend/apps/activities/views.py](backend/apps/activities/views.py) — DRF viewsets
- [frontend/src/stores/activityBlocks.js](frontend/src/stores/activityBlocks.js) — central Pinia store (fully wired to API; no mock data)
- [frontend/src/components/ActivityBlockGrid.vue](frontend/src/components/ActivityBlockGrid.vue) — interactive timeline grid
- [frontend/src/components/ActivityBlock.vue](frontend/src/components/ActivityBlock.vue) — individual block with resize handles
- [frontend/src/utils/date.js](frontend/src/utils/date.js) — date helpers (parseLocalDate, toLocalDateStr, makeLocalISO, getWeekNumber)
- [frontend/src/api/api.js](frontend/src/api/api.js) — Axios client setup
