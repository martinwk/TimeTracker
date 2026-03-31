We waren bezig met **stap 1: de backend**. Dit is waar we staan:

**Backend (Django) — status**
- ✅ Modellen uitgewerkt (`WindowActivity`, `ActivityBlock`, `UniqueActivity`, `ActivityRule`, `Project`, `TimeEntry`, `ActivityMapping`)
- ✅ AHK log importer (`import_ahk_log` management command + API endpoint)
- ✅ Aggregator (`aggregate_activities` management command + API endpoint)
- ✅ Auto-aggregatie na import
- ✅ Unit tests voor models, importer en aggregator
- ✅ DRF API — serializers + viewsets voor alle modellen (zodat de frontend data kan ophalen)
- ⬜ Rule engine — automatisch activiteiten aan projecten koppelen op basis van `ActivityRule`

**Frontend (Vue 3) — nog niet begonnen**
- ⬜ Vue 3 project opzetten met Vite
- ⬜ Dagoverzicht — tijdlijn van `ActivityBlock`s per dag
- ⬜ Project mapping scherm — `UniqueActivity` of blokken koppelen aan projecten
- ⬜ Uren invoer scherm — `TimeEntry` per project per dag invullen

**Afronden**
- ⬜ Tests uitbreiden voor de API
- ⬜ Admin bijwerken voor nieuwe modellen (`UniqueActivity`, `ActivityBlock`)