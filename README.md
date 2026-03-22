# Timetracker

Lichtgewicht Django-applicatie voor het koppelen van AHK-vensteractiviteiten aan projecten en werkuren.

## Opzetten

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Admin beschikbaar op http://localhost:8000/admin/

## Projectstructuur

```
timetracker/
├── config/
│   ├── settings.py
│   └── urls.py
├── activities/
│   ├── models.py       ← WindowActivity, ActivityRule
│   └── admin.py
├── projects/
│   ├── models.py       ← Project, TimeEntry, ActivityMapping
│   └── admin.py
├── manage.py
└── requirements.txt
```

## AHK-log importeren

```bash
python manage.py import_ahk_log pad/naar/window_log_2026-11.txt
```

(management command volgt in de volgende stap)

## Uitbreiden naar regex-regels

In `activities/models.py`, oncommentarieer in `MATCH_FIELD_CHOICES`:

```python
("title_regex", "Venstertitel (reguliere expressie)"),
("app_regex",   "Applicatienaam (reguliere expressie)"),
```

En in de `apply()`-methode de bijbehorende `elif`-takken.
Geen databasemigratie nodig voor bestaande regels.
