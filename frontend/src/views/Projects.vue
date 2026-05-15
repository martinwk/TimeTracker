<template>
  <div class="p-6 max-w-6xl mx-auto">

    <!-- Bovenbalk: zoekbalk + statusfilter + knop -->
    <div class="flex flex-wrap items-center gap-3 mb-6">
      <input
        data-testid="search-input"
        v-model="searchQuery"
        type="text"
        placeholder="Zoeken op naam…"
        class="flex-1 min-w-48 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />

      <div class="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
        <button
          data-testid="filter-actief"
          @click="statusFilter = 'actief'"
          :class="statusFilter === 'actief' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'"
          class="px-4 py-2 transition-colors"
        >Actief</button>
        <button
          data-testid="filter-alle"
          @click="statusFilter = 'alle'"
          :class="statusFilter === 'alle' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'"
          class="px-4 py-2 border-x border-gray-200 transition-colors"
        >Alle</button>
        <button
          data-testid="filter-gearchiveerd"
          @click="statusFilter = 'gearchiveerd'"
          :class="statusFilter === 'gearchiveerd' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'"
          class="px-4 py-2 transition-colors"
        >Gearchiveerd</button>
      </div>

      <button
        data-testid="btn-nieuw-project"
        @click="openNewForm"
        class="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
      >
        <span class="text-base leading-none">+</span> Nieuw project
      </button>
    </div>

    <!-- Kaartengrid -->
    <div
      v-if="filteredProjects.length > 0"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <div
        v-for="project in filteredProjects"
        :key="project.id"
        data-testid="project-card"
        class="group rounded-xl overflow-hidden border border-gray-200 bg-white shadow-sm flex flex-col"
      >
        <!-- Kleurindicator -->
        <div
          data-testid="project-color"
          :data-color="project.color"
          :style="{ backgroundColor: project.color }"
          class="h-2 flex-shrink-0"
        />

        <div class="p-4 flex flex-col flex-1">
          <!-- Naam + badge -->
          <div class="flex items-center gap-2 mb-1 min-w-0">
            <h3 class="font-semibold text-gray-900 truncate">{{ project.name }}</h3>
            <span
              v-if="!project.is_active"
              data-testid="badge-gearchiveerd"
              class="flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500"
            >Gearchiveerd</span>
          </div>

          <!-- Notities preview -->
          <p
            v-if="project.notes"
            class="text-sm text-gray-400 truncate mb-3"
          >{{ project.notes }}</p>
          <div v-else class="mb-3" />

          <!-- Actieknoppen: verschijnen bij hover op de kaart -->
          <div class="flex gap-1 mt-auto opacity-0 group-hover:opacity-100 transition-opacity duration-150">
            <button
              data-testid="btn-bewerken"
              @click="openEditForm(project)"
              title="Bewerken"
              class="relative group/btn rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-800 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
              <span class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded bg-gray-800 px-2 py-0.5 text-xs text-white opacity-0 group-hover/btn:opacity-100 transition-opacity">Bewerken</span>
            </button>

            <button
              v-if="project.is_active"
              data-testid="btn-archiveren"
              @click="handleArchive(project)"
              title="Archiveren"
              class="relative group/btn rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-800 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="21 8 21 21 3 21 3 8"/>
                <rect x="1" y="3" width="22" height="5"/>
                <line x1="10" y1="12" x2="14" y2="12"/>
              </svg>
              <span class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded bg-gray-800 px-2 py-0.5 text-xs text-white opacity-0 group-hover/btn:opacity-100 transition-opacity">Archiveren</span>
            </button>
            <button
              v-else
              data-testid="btn-activeren"
              @click="handleActivate(project)"
              title="Activeren"
              class="relative group/btn rounded-md p-2 text-indigo-500 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="17 1 21 5 17 9"/>
                <path d="M3 11V9a4 4 0 0 1 4-4h14"/>
                <polyline points="7 23 3 19 7 15"/>
                <path d="M21 13v2a4 4 0 0 1-4 4H3"/>
              </svg>
              <span class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded bg-gray-800 px-2 py-0.5 text-xs text-white opacity-0 group-hover/btn:opacity-100 transition-opacity">Activeren</span>
            </button>

            <button
              data-testid="btn-verwijderen"
              @click="handleDelete(project)"
              title="Verwijderen"
              class="relative group/btn rounded-md p-2 text-red-400 hover:bg-red-50 hover:text-red-600 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                <path d="M10 11v6M14 11v6"/>
                <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
              </svg>
              <span class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded bg-gray-800 px-2 py-0.5 text-xs text-white opacity-0 group-hover/btn:opacity-100 transition-opacity">Verwijderen</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Lege toestand -->
    <div
      v-else
      data-testid="empty-message"
      class="flex flex-col items-center justify-center py-16 text-gray-400"
    >
      <span class="text-4xl mb-3">📂</span>
      <p class="text-sm">Geen projecten gevonden.</p>
    </div>

    <!-- Formulier modal -->
    <div
      v-if="isFormOpen"
      data-testid="project-form"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      @click.self="closeForm"
    >
        <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
          <h2 class="text-base font-semibold text-gray-900 mb-4">
            {{ editingProject ? 'Project bewerken' : 'Nieuw project' }}
          </h2>

          <div class="space-y-4">
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Naam</label>
              <input
                data-testid="form-name"
                v-model="form.name"
                type="text"
                placeholder="Projectnaam"
                class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Kleur</label>
              <input
                data-testid="form-color"
                v-model="form.color"
                type="color"
                class="h-9 w-16 cursor-pointer rounded border border-gray-200 p-0.5"
              />
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Notities</label>
              <textarea
                data-testid="form-notes"
                v-model="form.notes"
                rows="3"
                placeholder="Optionele notities…"
                class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
              />
            </div>
          </div>

          <div class="flex justify-end gap-2 mt-6">
            <button
              data-testid="btn-annuleren"
              @click="closeForm"
              class="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
            >Annuleren</button>
            <button
              data-testid="btn-opslaan"
              @click="saveProject"
              class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
            >Opslaan</button>
          </div>
        </div>
      </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'

const store = useProjectsStore()

const searchQuery  = ref('')
const statusFilter = ref('actief')
const isFormOpen   = ref(false)
const editingProject = ref(null)
const form = ref({ name: '', color: '#4F86C6', notes: '' })

const filteredProjects = computed(() => {
  let list = store.projects

  if (statusFilter.value === 'actief') {
    list = list.filter(p => p.is_active)
  } else if (statusFilter.value === 'gearchiveerd') {
    list = list.filter(p => !p.is_active)
  }

  const q = searchQuery.value.trim().toLowerCase()
  if (q) list = list.filter(p => p.name.toLowerCase().includes(q))

  return list
})

function openNewForm() {
  editingProject.value = null
  form.value = { name: '', color: '#4F86C6', notes: '' }
  isFormOpen.value = true
}

function openEditForm(project) {
  editingProject.value = project
  form.value = { name: project.name, color: project.color, notes: project.notes }
  isFormOpen.value = true
}

function closeForm() {
  isFormOpen.value = false
  editingProject.value = null
}

async function saveProject() {
  if (editingProject.value) {
    await store.updateProject(editingProject.value.id, { ...form.value })
  } else {
    await store.createProject({ ...form.value })
  }
  closeForm()
}

async function handleArchive(project) {
  await store.updateProject(project.id, { is_active: false })
}

async function handleActivate(project) {
  await store.updateProject(project.id, { is_active: true })
}

async function handleDelete(project) {
  await store.deleteProject(project.id)
}

onMounted(() => store.fetchProjects())
</script>
