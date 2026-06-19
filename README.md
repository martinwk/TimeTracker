# TimeTracker

Lichtgewicht tool voor tijdregistratie op basis van AutoHotkey vensteractiviteiten. AHK logt automatisch welke vensters actief zijn; TimeTracker zet die ruwe log om naar tijdblokken en laat je die koppelen aan projecten via een visuele tijdlijn.

## Hoe het werkt

```
AHK vensterlog (tekstbestand)
  → importeer via de API of beheerpagina
  → WindowActivity records (onbewerkt, nooit gewijzigd)
  → Aggregator groepeert opeenvolgende activiteiten → ActivityBlocks
  → Tijdlijn in de frontend: blokken toewijzen aan projecten
      - handmatig via ProjectSelector
      - automatisch via ActivityRules (prioriteitsgebaseerd)
  → BlockProjectHistory houdt elke toewijzing bij (audit trail)
```

## Technische stack

| Laag | Technologie |
|---|---|
| Backend | Django 4.2 + Django REST Framework |
| Database | SQLite (ontwikkeling) |
| Frontend | Vue 3 (Composition API) + Vite + Pinia + Tailwind CSS 4 |
| HTTP client | Axios |
| Tests | pytest + pytest-django |

## Projectstructuur

```
TimeTracker/
├── backend/
│   ├── config/               # settings, urls, wsgi
│   └── apps/
│       ├── activities/       # kern: vensteractiviteiten, blokken, regels
│       │   ├── models.py     # WindowActivity, ActivityBlock, UniqueActivity, ActivityRule
│       │   ├── importer.py   # parser voor AHK-logs
│       │   ├── aggregator.py # groepeert activiteiten tot blokken
│       │   ├── rule_engine.py
│       │   └── views.py      # DRF viewsets + import/apply-rules endpoints
│       └── projects/         # Project model
└── frontend/
    └── src/
        ├── views/            # Dashboard, Projects, Weekstaat, Stats, Rules
        ├── components/       # ActivityBlockGrid, ActivityBlock, ProjectSelector, SettingsPanel
        ├── stores/           # activityBlocks.js, projects.js, activityRules.js (Pinia)
        └── api/              # Axios client (baseURL: http://localhost:8000/api)
```

## Opzetten en starten

**Backend:**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

**Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

Beide moeten tegelijk draaien. Admin beschikbaar op http://localhost:8000/admin/.

**Tests:**
```powershell
cd backend
pytest
```

## Kernmodellen

| Model | Doel |
|---|---|
| `WindowActivity` | Ruwe AHK-loginregel. Onveranderlijk na import. |
| `ActivityBlock` | Geaggregeerd blok (opeenvolgende activiteiten, zelfde app). Optionele FK naar Project. |
| `UniqueActivity` | Unieke venstertitels binnen een blok, gesorteerd op duur. |
| `ActivityRule` | Patroongebaseerde automatische toewijzing. Volgorde bepaald door prioriteit (lager = eerst). |
| `Project` | Doelproject met kleur (hex) voor tijdlijnweergave. |
| `BlockProjectHistory` | Auditlog: welk project, wanneer, door regel of handmatig. |

## API-endpoints

| Methode | URL | Doel |
|---|---|---|
| POST | `/api/activities/import/` | AHK-log uploaden (multipart) |
| POST | `/api/activities/sync/` | Log importeren + alle dagen herberekenen |
| POST | `/api/activities/apply-rules/` | Regelengine uitvoeren |
| GET | `/api/activities/activity-blocks/` | Blokken ophalen (filterbaar op datum, app, project) |
| GET/POST/PATCH/DELETE | `/api/activities/activity-rules/` | CRUD voor regels |
| GET | `/api/projects/` | Projecten ophalen |

## Ontwerpkeuzes

- **Onveranderlijke import:** WindowActivity records worden na import nooit gewijzigd. Aggregatie maakt afgeleide records die opnieuw gegenereerd kunnen worden.
- **Prioriteitsgebaseerde regels:** Eerste overeenkomst wint. Geen gestapelde regeltoepassing.
- `is_noise` filtert laagwaardige activiteiten (Idle, Program Manager) weg uit de UI, maar bewaart ze in de database.
- **App-naamextractie:** Heuristisch — probeert separatoren als `" - "` of `" — "`, valt terug op volledige venstertitel.
- **Visueel samenvoegen:** Aangrenzende blokken met hetzelfde project worden samengevoegd weergegeven (`mergedBlocksByDay` in Pinia), maar bewerkingen werken nog steeds op individuele blokken.
- Tijden worden opgeslagen in UTC; de frontend toont Europe/Amsterdam.

## Huidige status

Backend en frontend zijn volledig gekoppeld. Drag-interface werkt (verslepen, verkleinen/vergroten, rangeselecties, projecttoewijzing) en slaat op via de API. Mock data is verwijderd.

Beschikbare pagina's:

- **Dashboard** — visuele tijdlijn met blokken per dag; gedeclareerde uren zichtbaar in dag-headers
- **Weekstaat** — uren-per-project-matrix op basis van wandkloktijd (kwartierblokken)
- **Projects** — CRUD-beheer voor projecten
- **Regels** — CRUD-beheer voor auto-assign regels (prioriteit, veld, waarde, project); knop "Regels toepassen" voor de huidige week
- **Stats** — statistiekenpagina (in ontwikkeling)

Klikken op een toegewezen blok toont een heroewijzings-popup; via "Koppeling verwijderen" wordt een aggregator-blok losgekoppeld (blijft zichtbaar als grijs blok). Handmatige ontkoppelingen overleven herberekening via `BlockProjectHistory`.

De sync-knop (links onderin de sidebar) importeert het AHK-logbestand en herberekent alle betrokken dagen. Het tandwiel ernaast opent het instellingenpaneel met: logpadinstelling (opgeslagen in localStorage), bestandsimport via filepicker, en een knop "Regels opnieuw toepassen".

## Regex-regels uitbreiden

In `activities/models.py`, uncommentarieer in `MATCH_FIELD_CHOICES`:

```python
("title_regex", "Venstertitel (reguliere expressie)"),
("app_regex",   "Applicatienaam (reguliere expressie)"),
```

En in de `apply()`-methode de bijbehorende `elif`-takken. Geen databasemigratie nodig voor bestaande regels.
