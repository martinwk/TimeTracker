# Vue 3 Setup Guide voor Beginners

## Inleiding

Dit is een stap-voor-stap gids voor het opzetten van je Vue 3 project. Ik zal alles uitleggen in eenvoudige taal.

### Wat is Vue?
Vue is een **JavaScript framework** - een toolkit waarmee je interactieve webpagina's bouwt.
- In plaats van alles handmatig met HTML te doen, kun je components gebruiken (herbruikbare stukken UI)
- Vue laat dingen real-time bijwerken zonder de pagina te verversen

### Wat is Vite?
Vite is een **build tool** - het helpt je Vue-code om te zetten in iets dat browsers kunnen gebruiken.

### Wat is npm?
npm is **Package Manager** - een hulpmiddel waarmee je libraries installeert (externe code die anderen hebben geschreven).

---

## STAP 1: Node.js installeren

Dit is het **allereerste** wat je nodig hebt.

### Wat is Node.js?
Node.js laat je JavaScript op je computer runnen (niet alleen in een browser).

### Hoe installeert?

1. Ga naar https://nodejs.org/
2. Download de **LTS** versie (Long Term Support - stabiel)
3. Volg de installer, klik overal "Next" en "Install"
4. **Restart je computer**

### Controleer of het werkt:

Open **Git Bash** en typ:

```bash
node --version
npm --version
```

Je zou iets als dit moeten zien:
```
v22.x.x
10.x.x
```

**Belangrijk:** Je ziet NUMMERS. Geen foutmelding? Goed! ✅

---

## STAP 2: Ga naar je TimeTracker repo

Je gaat de Vue app als **subfolder** in je TimeTracker repo maken.

### Stap voor stap:

1. Open **Git Bash**
2. Navigeer naar je TimeTracker repo:

```bash
cd /c/Users/mwkor/Repositories/TimeTracker
```

Opmerking: Git Bash gebruikt `/c/` voor C: drive (Unix-style paths)

Je zou nu moeten zien:
```
mwkor@COMPUTER MINGW64 /c/Users/mwkor/Repositories/TimeTracker
```

Dit betekent: je bent IN de TimeTracker map! ✅

---

## STAP 3: Maak het Vue project aan als `frontend` subfolder

Nu gaan we Vite gebruiken om een Vue project te genereren IN je repo.

### Wat we gaan doen:
Vite maakt een kant-en-klaar project voor ons met alle bestandsstructuur.

### Tik dit in de terminal:

```bash
npm create vite@latest frontend -- --template vue
```

Dit doet:
- `npm create vite@latest` = "Maak een nieuw Vite project"
- `frontend` = Naam van de map (dit is waar je project in komt)
- `--template vue` = "Ik wil Vue gebruiken"

**Wacht tot het klaar is.** Je ziet veel tekst voorbijkomen.

---

## STAP 4: Open het project

Nu gaan we INTO het project.

### Typ in de terminal:

```bash
cd frontend
```

Dit betekent: "Change Directory" = ga naar de `frontend` map.

Nu zou je terminal moeten zeggen:
```
C:\Users\mwkor\Repositories\TimeTrackerGUI\frontend>
```

---

## STAP 5: Installeer de dependencies

"Dependencies" = externe libraries die je project nodig heeft.

### Typ dit:

```bash
npm install
```

Dit doet:
1. Leest het `package.json` bestand (receptenlijst van wat je nodig hebt)
2. **Downloadt alles** van het internet
3. Zet het in de `node_modules` folder

**Dit kan 2-3 minuten duren.** Geduld! ☕

Je ziet veel tekst. Aan het einde moet je zien:
```
added XXX packages, and audited XXX packages in Xm
```

**Belangrijk:** Geen fout? Goed! ✅

---

## STAP 6: Installeer extra libraries die WE nodig hebben

Nu installeren we de libraries die we voor TimeTracker nodig hebben.

### Tik in terminal:

```bash
npm install axios pinia vue-router
```

Dit installeert:
- **axios** = Voor API calls (communicatie met Django backend)
- **pinia** = Voor "state management" (data opslaan/delen tussen componenten)
- **vue-router** = Voor navigatie (links naar verschillende pagina's)

**Wacht weer tot het klaar is.**

---

## STAP 7: Installeer Tailwind CSS (styling)

Tailwind helpt ons mooie UI te maken zonder veel CSS te schrijven.

> **Let op:** We gebruiken Tailwind v4. Dit werkt anders dan v3 — geen config bestanden meer nodig!

### Installeer Tailwind en de Vite plugin:

```bash
npm install -D tailwindcss @tailwindcss/vite
```

De `-D` betekent "development only" - dit is code die we alleen tijdens development nodig hebben.

**Geen fout? Goed!** ✅

---

## STAP 8: Voeg Tailwind toe aan Vite

In v4 koppelen we Tailwind direct aan Vite via een plugin — geen apart PostCSS config bestand nodig.

### Open bestand: `vite.config.js`

Je ziet:
```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
})
```

### **VERANDER** het naar:

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss()
  ],
})
```

### Sla op (Ctrl+S)

---

## STAP 9: Voeg Tailwind toe aan je CSS

In v4 activeer je Tailwind met één regel in je CSS bestand — geen `tailwind.config.js` nodig!

### Open bestand: `src/style.css`

Voeg dit toe als **allereerste regel** (vóór al je eigen stijlen):

```css
@import "tailwindcss";

/* jouw eigen stijlen hieronder */
```

### Sla op (Ctrl+S)

Dat is alles! Tailwind v4 detecteert automatisch welke bestanden het moet scannen. ✅

---

## STAP 10: Start de development server

Nu gaan we het project proberen!

### Typ in terminal:

```bash
npm run dev
```

Dit doet:
1. Start een development server
2. Opent een live preview van je project
3. **Automatisch refresh** als je code wijzigt (magic! ✨)

**Wacht even en je ziet iets als:**
```
  VITE v6.X.X  ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

Dit is GOED! ✅

---

## STAP 11: Controleer in browser

### Open je browser:

1. Ga naar: `http://localhost:5173/`
2. Je zou de Vue welkomsscherm moeten zien

🎉 **Gefeliciteerd! Je hebt Vue draaiend!**

---

## Huiswerk: Verken het project

Ga terug naar je editor (VS Code of welke je gebruikt) en kijk rond.

### Wat zie je?

```
frontend/
├── src/
│   ├── App.vue          ← Dit is de "root component"
│   ├── main.js          ← Entry point (waar alles begint)
│   ├── components/
│   │   └── HelloWorld.vue
│   ├── assets/          ← Plaatjes etc
│   └── style.css        ← Hier staat @import "tailwindcss"
├── public/
├── index.html           ← Main HTML bestand
├── vite.config.js       ← Vite instellingen (inclusief Tailwind plugin)
├── package.json         ← Project meta data
└── node_modules/        ← Alles wat npm installeerde
```

> **Verschil met v3:** Je ziet geen `tailwind.config.js` of `postcss.config.js` meer. Dat is normaal — die zijn in v4 niet meer nodig!

### Wat is wat?

- **src/** = Jouw code (Vue componenten, JavaScript, etc)
- **node_modules/** = Gedownloade libraries (niet aanraken!)
- **public/** = Static files (afbeeldingen etc)
- **index.html** = Root HTML pagina
- **package.json** = "Receptenlijst" van dependencies

---

## STAP 12: Maak je eerste component

Nu gaan we **opschonen** en je eerste component maken.

### Open: `src/App.vue`

Je ziet veel code. Vervang ALLES met:

```vue
<template>
  <div class="min-h-screen bg-gray-100 p-8">
    <h1 class="text-4xl font-bold text-blue-600">
      🎉 TimeTracker Vue App
    </h1>
    <p class="text-gray-700 mt-4">
      Hello World! Ik ben aan het leren met Vue.
    </p>
  </div>
</template>

<script setup>
// Hier comes JavaScript
// Voor nu: leeg, want we hebben geen functies nodig
</script>

<style scoped>
/* Tailwind style - we gebruiken Tailwind, dus meestal leeg */
</style>
```

### Wat is wat?

1. **`<template>`** = HTML (wat je ziet op je scherm)
   - Dit is bijna normaal HTML
   - `class="text-4xl font-bold..."` = Tailwind classes
   - `text-4xl` = hele grote text
   - `font-bold` = vet
   - `text-blue-600` = blauwe kleur

2. **`<script setup>`** = JavaScript (de "intelligentie")
   - Hier schrijven we logica
   - Voor nu leeg

3. **`<style scoped>`** = CSS (extra styling)
   - Scoped = alleen voor dit component
   - Wij gebruiken Tailwind, dus dit blijft meestal leeg

### Sla op (Ctrl+S)

**Browser updated vanzelf!** ✨

Je zou nu moeten zien:
```
🎉 TimeTracker Vue App
Hello World! Ik ben aan het leren met Vue.
```

---

## STAP 13: Maak Sidebar component

Nu maken we je **eerste echt component**.

### Maak nieuw bestand:

1. Rechtsklik op `src/components/`
2. "New File" → `Sidebar.vue`

### Tik dit in:

```vue
<template>
  <nav class="w-64 bg-gray-800 text-white p-6 min-h-screen">
    <h2 class="text-2xl font-bold mb-8">TimeTracker</h2>

    <!-- Menu items -->
    <ul class="space-y-4">
      <li>
        <a href="#" class="hover:text-blue-400">
          📊 Dashboard
        </a>
      </li>
      <li>
        <a href="#" class="hover:text-blue-400">
          📁 Projects
        </a>
      </li>
      <li>
        <a href="#" class="hover:text-blue-400">
          📝 Activity Blocks
        </a>
      </li>
      <li>
        <a href="#" class="hover:text-blue-400">
          ⚙️ Rules
        </a>
      </li>
    </ul>
  </nav>
</template>

<script setup>
// Nog niks nodig!
</script>

<style scoped>
/* Tailwind doet het werk */
</style>
```

### Wat doet dit?

- `<nav>` = Navigation menu (zijbalk)
- `w-64` = Breedte 64 units
- `bg-gray-800` = Donkergrijze achtergrond
- `space-y-4` = Ruimte tussen menu items
- `hover:text-blue-400` = Blauw als je eroverheen gaat

---

## STAP 14: Gebruik Sidebar in App.vue

Nu gaan we deze component in App.vue gebruiken.

### Update `App.vue`:

```vue
<template>
  <div class="flex">
    <!-- Sidebar links -->
    <Sidebar />

    <!-- Inhoud rechts -->
    <main class="flex-1 bg-gray-100 p-8">
      <h1 class="text-4xl font-bold text-blue-600">
        🎉 TimeTracker Vue App
      </h1>
      <p class="text-gray-700 mt-4">
        Hello World! Ik ben aan het leren met Vue.
      </p>
    </main>
  </div>
</template>

<script setup>
// IMPORTEER het Sidebar component
import Sidebar from './components/Sidebar.vue'
</script>

<style scoped>
</style>
```

### Wat nieuw is?

- `import Sidebar from './components/Sidebar.vue'` = "Laad het Sidebar component"
- `<Sidebar />` = "Toon het component hier"
- `<main class="flex-1">` = "Take all remaining space"
- `<div class="flex">` = "Zet items naast elkaar" (flex = flexbox)

### Sla op!

**Je zou nu moeten zien: een grijze zijbalk links met menu items!** 🎉

---

## STAP 15: Maak je eerste STATE

"State" = data die kan veranderen.

Laten we een counter maken als voorbeeld.

### Update `App.vue`:

```vue
<template>
  <div class="flex">
    <Sidebar />

    <main class="flex-1 bg-gray-100 p-8">
      <h1 class="text-4xl font-bold text-blue-600">
        🎉 TimeTracker Vue App
      </h1>

      <!-- NIEUWE CODE: Counter -->
      <div class="mt-8 bg-white p-6 rounded-lg shadow">
        <h2 class="text-2xl font-bold mb-4">Counter Example</h2>

        <!-- Toon het getal -->
        <p class="text-xl mb-4">
          Counter: <span class="font-bold text-blue-600">{{ count }}</span>
        </p>

        <!-- Knoppen om het getal te veranderen -->
        <div class="flex gap-4">
          <button
            @click="count = count + 1"
            class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            + Increment
          </button>
          <button
            @click="count = count - 1"
            class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            - Decrement
          </button>
          <button
            @click="count = 0"
            class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Reset
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'  // ← Import ref
import Sidebar from './components/Sidebar.vue'

// STATE: een getal dat kan veranderen
const count = ref(0)

// `ref(0)` betekent: "Dit is een reactive waarde, start met 0"
// "Reactive" = Vue let op veranderingen en update scherm automatisch
</script>

<style scoped>
</style>
```

### Wat is NEW?

```javascript
import { ref } from 'vue'
const count = ref(0)
```

Dit maakt **state** - een waarde die kan veranderen.

```html
{{ count }}
```

Dit toont de waarde in HTML (dubbele brackets = "voeg JavaScript in").

```html
@click="count = count + 1"
```

Dit betekent: "Als geklikt, doe count = count + 1" (verhoog met 1).

### Test het!

Klik de knoppen. Het getal verandert! 🎉

---

## STAP 16: Communiceer met Django API
<span style="color:red">

**>>>>>>>>>>>>>>>>**

**HIER BEN IK GEBLEVEN**

**HIER BEN IK GEBLEVEN**

**HIER BEN IK GEBLEVEN**

**HIER BEN IK GEBLEVEN**

**<<<<<<<<<<<<<<<<**

</span>

Nu gaat het interessant! We gaan data van Django halen.

### Maak API client folder:

1. Rechtsklik op `src/`
2. New Folder → `api`

### Maak bestand: `src/api/client.js`

```javascript
// Dit bestand configureert axios (de HTTP client)

import axios from 'axios'

// Maak een axios "instance" met Django als baseURL
const client = axios.create({
  baseURL: 'http://localhost:8000/api',  // ← Django runs op 8000
  headers: {
    'Content-Type': 'application/json',
  },
})

// Export zodat andere bestanden het kunnen gebruiken
export default client
```

### Maak bestand: `src/api/projects.js`

```javascript
// Dit bestand bevat functies om projects op te halen

import client from './client'

// Functie: Haal alle projecten op
export async function getProjects() {
  try {
    // GET request naar /api/projects/
    const response = await client.get('/projects/')

    // Response kan nested data hebben (results: [...])
    // Dus: return data.results OR data (fallback)
    return response.data.results || response.data
  } catch (error) {
    console.error('Error fetching projects:', error)
    throw error  // Gooi error door zodat App.vue het kan opvangen
  }
}

// Functie: Maak nieuw project
export async function createProject(name, color) {
  try {
    const response = await client.post('/projects/', {
      name: name,
      color: color,
      is_active: true,
    })
    return response.data
  } catch (error) {
    console.error('Error creating project:', error)
    throw error
  }
}
```

### Uitleg:

```javascript
export async function getProjects() {
```

- `export` = "Exporteer zodat andere bestanden dit kunnen gebruiken"
- `async` = "Dit kan lang duren (wachten op internet), don't block"

```javascript
const response = await client.get('/projects/')
```

- `await` = "Wacht tot het klaar is, voer dan door"
- `client.get()` = HTTP GET request

---

## STAP 17: Toon projecten in App

Update `App.vue`:

```vue
<template>
  <div class="flex">
    <Sidebar />

    <main class="flex-1 bg-gray-100 p-8">
      <h1 class="text-4xl font-bold text-blue-600">
        🎉 TimeTracker Vue App
      </h1>

      <!-- Projects Section -->
      <div class="mt-8 bg-white p-6 rounded-lg shadow">
        <h2 class="text-2xl font-bold mb-4">Projects from Django</h2>

        <!-- Loading indicator -->
        <div v-if="loading" class="text-gray-600">
          Loading projects...
        </div>

        <!-- Error message -->
        <div v-if="error" class="text-red-600">
          Error: {{ error }}
        </div>

        <!-- Projects list -->
        <div v-if="!loading && projects.length > 0" class="space-y-3">
          <div
            v-for="project in projects"
            :key="project.id"
            class="p-4 border border-gray-300 rounded"
          >
            <h3 class="font-bold text-lg">{{ project.name }}</h3>
            <p class="text-sm text-gray-600">Color: {{ project.color }}</p>
            <p class="text-sm text-gray-600">Active: {{ project.is_active }}</p>
          </div>
        </div>

        <!-- No projects -->
        <div v-if="!loading && projects.length === 0" class="text-gray-600">
          No projects found
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import { getProjects } from './api/projects'

// STATE
const projects = ref([])  // Lege array (gaat gevuld worden)
const loading = ref(false)  // Zijn we aan het laden?
const error = ref(null)  // Error message

// FUNCTIE: Fetch projects van Django
async function loadProjects() {
  loading.value = true
  error.value = null

  try {
    const data = await getProjects()
    projects.value = data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false  // Finally = altijd, loading of error
  }
}

// onMounted = "Als component geladen is, voer dan uit"
onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
</style>
```

### Wat is NEW?

```html
<div v-if="loading">Loading...</div>
```
- `v-if` = "Toon dit ALLEEN als loading true is"

```html
<div v-for="project in projects" :key="project.id">
```
- `v-for` = "Loop door alle projects"
- `:key` = "Unieke identifier per item" (helpt Vue om updates te volgen)

```html
{{ project.name }}
```
- Toon project naam

```javascript
onMounted(() => {
  loadProjects()
})
```
- Na component loaded, fetch projects

---

## STAP 18: Enable CORS in Django

Django blokkeert requests van andere websites standaard. Vite draait op 5173, Django op 8000 = ander "origin".

### Install in Django:

In je Django terminal (niet Vue terminal!):

```bash
pip install django-cors-headers
```

### Configureer Django:

Open `config/settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    # ... andere apps ...
    'corsheaders',  # ← Voeg toe
    'activities',
    'projects',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ← Zet BOVENAAN!
    'django.middleware.security.SecurityMiddleware',
    # ... rest ...
]

# Voeg onderaan toe:
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vue dev server
    "http://localhost:3000",  # Backup port
]
```

### Test:

Ga terug naar browser (Vue app). Je zou projecten moeten zien!

---

## STAP 19: Controleer alles

### Checklist:

- [ ] Node.js geïnstalleerd? (check met `node --version`)
- [ ] Vue project gemaakt? (folder `frontend` bestaat)
- [ ] `npm install` gerund?
- [ ] `npm run dev` draait? (http://localhost:5173/ werkt)
- [ ] Sidebar zichtbaar?
- [ ] Counter knop werkt?
- [ ] Projects van Django tonen?
- [ ] CORS configured in Django?

**Alles groen?** Geweldig! Je hebt de foundation! 🎉

---

## Volgende Stappen

Nu je de **basics** kent, gaan we:

1. **Pinia stores** bouwen (state management)
2. **Router** toevoegen (verschillende pagina's)
3. **Activity Blocks** component
4. **Project Selector** component
5. Stap voor stap, altijd testbaar

Je kan nu **experimenteren**! Probeer:
- Meer components maken
- Meer state aan App.vue toevoegen
- Meer API functies maken

**Maak het jezelf eigen!** 🚀

---

## Troubleshooting

### Port 5173 al in gebruik?
```bash
npm run dev -- --port 5174
```

### Tailwind classes werken niet?
- Staat `@import "tailwindcss";` bovenaan `src/style.css`?
- Staat de `tailwindcss()` plugin in `vite.config.js`?
- Is `@tailwindcss/vite` geïnstalleerd? (check met `npm list @tailwindcss/vite`)

### Kan Django API niet bereiken?
- Django draait op 8000? (`python manage.py runserver`)
- CORS configured?
- Juiste URL in `api/client.js`? (`http://localhost:8000/api`)

### Module niet gevonden?
- Je hebt alle `npm install` commando's gerund?
- Node restarted?

### Syntax error?
- Controleer spaties/haakjes
- Console zegt waar het fout is

---

## Je volgende oproep:

Wanneer je:
1. Dit allemaal hebt gedaan
2. Projecten van Django ziet in Vue
3. Bereid bent voor stap 2

**Laat me weten, dan bouwen we Pinia stores!** 👍