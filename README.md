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
        ├── views/            # Dashboard, Projects, Stats
        ├── components/       # ActivityBlockGrid, ActivityBlock, ProjectSelector
        ├── stores/           # activityBlocks.js (Pinia)
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
| POST | `/api/activities/apply-rules/` | Regelengine uitvoeren |
| GET | `/api/activities/activity-blocks/` | Blokken ophalen (filterbaar op datum, app, project) |
| GET/POST/PATCH | `/api/activities/activity-rules/` | CRUD voor regels |
| GET | `/api/projects/` | Projecten ophalen |

## Ontwerpkeuzes

- **Onveranderlijke import:** WindowActivity records worden na import nooit gewijzigd. Aggregatie maakt afgeleide records die opnieuw gegenereerd kunnen worden.
- **Prioriteitsgebaseerde regels:** Eerste overeenkomst wint. Geen gestapelde regeltoepassing.
- `is_noise` filtert laagwaardige activiteiten (Idle, Program Manager) weg uit de UI, maar bewaart ze in de database.
- **App-naamextractie:** Heuristisch — probeert separatoren als `" - "` of `" — "`, valt terug op volledige venstertitel.
- **Visueel samenvoegen:** Aangrenzende blokken met hetzelfde project worden samengevoegd weergegeven (`mergedBlocksByDay` in Pinia), maar bewerkingen werken nog steeds op individuele blokken.
- Tijden worden opgeslagen in UTC; de frontend toont Europe/Amsterdam.

## Huidige status

Backend grotendeels klaar (modellen, importer, aggregator, regelengine, API). Frontend heeft een volledig interactieve UI maar **alle API-aanroepen zijn momenteel uitgecommentarieerd** — de store gebruikt mockdata. Volgende stap: frontend koppelen aan de live API.

Nog te doen:
- API-aanroepen activeren in `frontend/src/stores/activityBlocks.js`
- Projectenpagina (CRUD)
- Statistiekenpagina
- Backend API-tests uitbreiden

## Regex-regels uitbreiden

In `activities/models.py`, uncommentarieer in `MATCH_FIELD_CHOICES`:

```python
("title_regex", "Venstertitel (reguliere expressie)"),
("app_regex",   "Applicatienaam (reguliere expressie)"),
```

En in de `apply()`-methode de bijbehorende `elif`-takken. Geen databasemigratie nodig voor bestaande regels.
