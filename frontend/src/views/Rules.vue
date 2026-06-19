<template>
  <div class="p-6 max-w-4xl mx-auto">

    <!-- Bovenbalk: titel + knoppen -->
    <div class="flex flex-wrap items-center gap-3 mb-6">
      <h1 class="text-xl font-semibold text-gray-900 flex-1">Automatische toewijzingsregels</h1>

      <button
        data-testid="btn-regels-toepassen"
        @click="handleApplyRules"
        :disabled="applying"
        class="flex items-center gap-1.5 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-colors"
      >
        <svg class="w-4 h-4" :class="{ 'animate-spin': applying }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Regels toepassen
      </button>

      <button
        data-testid="btn-nieuwe-regel"
        @click="openNewForm"
        class="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
      >
        <span class="text-base leading-none">+</span> Nieuwe regel
      </button>
    </div>

    <!-- Feedback: regels toepassen -->
    <p
      v-if="applySuccess"
      data-testid="apply-success"
      class="mb-4 rounded-lg bg-green-50 px-4 py-2 text-sm text-green-700"
    >
      Regels succesvol toegepast.
    </p>
    <p
      v-if="applyError"
      data-testid="apply-error"
      class="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600"
    >
      {{ applyError }}
    </p>

    <!-- Tabel met regels -->
    <div v-if="sortedRules.length > 0" class="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide">
          <tr>
            <th class="px-4 py-3 text-left w-16">Prioriteit</th>
            <th class="px-4 py-3 text-left">Veld</th>
            <th class="px-4 py-3 text-left">Waarde</th>
            <th class="px-4 py-3 text-left">Project</th>
            <th class="px-4 py-3 text-center w-20">Actief</th>
            <th class="px-4 py-3 text-right w-24">Acties</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr
            v-for="rule in sortedRules"
            :key="rule.id"
            data-testid="rule-row"
            class="hover:bg-gray-50 transition-colors"
          >
            <td class="px-4 py-3 text-gray-500 tabular-nums">{{ rule.priority }}</td>
            <td class="px-4 py-3 text-gray-700">{{ rule.match_field_display }}</td>
            <td class="px-4 py-3 font-mono text-gray-800">{{ rule.match_value }}</td>
            <td class="px-4 py-3 text-gray-700">{{ projectName(rule.project) }}</td>
            <td class="px-4 py-3 text-center">
              <span
                :class="rule.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
                class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
              >
                {{ rule.is_active ? 'Ja' : 'Nee' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex justify-end gap-1">
                <button
                  data-testid="btn-bewerken"
                  @click="openEditForm(rule)"
                  title="Bewerken"
                  class="relative group/btn rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-800 transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                  <span class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded bg-gray-800 px-2 py-0.5 text-xs text-white opacity-0 group-hover/btn:opacity-100 transition-opacity">Bewerken</span>
                </button>
                <button
                  data-testid="btn-verwijderen"
                  @click="handleDelete(rule)"
                  title="Verwijderen"
                  class="relative group/btn rounded-md p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 transition-colors"
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
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Lege toestand -->
    <div
      v-else
      data-testid="empty-message"
      class="flex flex-col items-center justify-center py-16 text-gray-400"
    >
      <span class="text-4xl mb-3">📋</span>
      <p class="text-sm">Geen regels gevonden. Maak een nieuwe regel aan.</p>
    </div>

    <!-- Formulier modal -->
    <div
      v-if="isFormOpen"
      data-testid="rule-form"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      @click.self="closeForm"
    >
      <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h2 class="text-base font-semibold text-gray-900 mb-4">
          {{ editingRule ? 'Regel bewerken' : 'Nieuwe regel' }}
        </h2>

        <div class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Prioriteit</label>
            <input
              data-testid="form-priority"
              v-model.number="form.priority"
              type="number"
              min="1"
              placeholder="10"
              class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>

          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Veld</label>
            <select
              data-testid="form-match-field"
              v-model="form.match_field"
              class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              <option v-for="opt in matchFieldOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Waarde</label>
            <input
              data-testid="form-match-value"
              v-model="form.match_value"
              type="text"
              placeholder="bijv. VS Code"
              class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>

          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Project</label>
            <select
              data-testid="form-project"
              v-model.number="form.project"
              class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              <option value="">-- Kies een project --</option>
              <option v-for="p in projectsStore.projects" :key="p.id" :value="p.id">
                {{ p.name }}
              </option>
            </select>
          </div>

          <div class="flex items-center gap-2">
            <input
              data-testid="form-is-active"
              v-model="form.is_active"
              type="checkbox"
              id="form-is-active"
              class="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-400"
            />
            <label for="form-is-active" class="text-sm text-gray-700">Regel actief</label>
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
            @click="saveRule"
            class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
          >Opslaan</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useActivityRulesStore } from '@/stores/activityRules'
import { useProjectsStore } from '@/stores/projects'
import { useActivityBlocksStore } from '@/stores/activityBlocks'
import { parseLocalDate, toLocalDateStr } from '@/utils/date'

const rulesStore    = useActivityRulesStore()
const projectsStore = useProjectsStore()
const blocksStore   = useActivityBlocksStore()

const isFormOpen  = ref(false)
const editingRule = ref(null)
const applying    = ref(false)
const applySuccess = ref(false)
const applyError   = ref(null)

const form = ref({
  priority: 10,
  match_field: 'app_name',
  match_value: '',
  project: '',
  is_active: true,
})

const matchFieldOptions = [
  { value: 'app_name',          label: 'Applicatienaam (exact)' },
  { value: 'title_contains',    label: 'Venstertitel bevat' },
  { value: 'dominant_activity', label: 'Dominante activiteit' },
  { value: 'recent_project',    label: 'Recent project voor app' },
]

const sortedRules = computed(() =>
  [...rulesStore.rules].sort((a, b) => a.priority - b.priority)
)

function projectName(projectId) {
  const p = projectsStore.projects.find(p => p.id === projectId)
  return p ? p.name : `Project ${projectId}`
}

function openNewForm() {
  editingRule.value = null
  form.value = { priority: 10, match_field: 'app_name', match_value: '', project: '', is_active: true }
  isFormOpen.value = true
}

function openEditForm(rule) {
  editingRule.value = rule
  form.value = {
    priority:    rule.priority,
    match_field: rule.match_field,
    match_value: rule.match_value,
    project:     rule.project,
    is_active:   rule.is_active,
  }
  isFormOpen.value = true
}

function closeForm() {
  isFormOpen.value = false
  editingRule.value = null
}

async function saveRule() {
  const payload = { ...form.value }
  if (editingRule.value) {
    await rulesStore.updateRule(editingRule.value.id, payload)
  } else {
    await rulesStore.createRule(payload)
  }
  closeForm()
}

async function handleDelete(rule) {
  if (!window.confirm(`Regel "${rule.match_value}" verwijderen?`)) return
  await rulesStore.deleteRule(rule.id)
}

async function handleApplyRules() {
  applying.value = true
  applySuccess.value = false
  applyError.value = null
  try {
    const dateFrom = blocksStore.currentDate
    const d = parseLocalDate(dateFrom)
    d.setDate(d.getDate() + 6)
    const dateTo = toLocalDateStr(d.toISOString())
    const result = await rulesStore.applyRules(dateFrom, dateTo)
    if (result !== null) {
      applySuccess.value = true
    } else {
      applyError.value = rulesStore.error ?? 'Fout bij toepassen regels'
    }
  } finally {
    applying.value = false
  }
}

onMounted(() => {
  rulesStore.fetchRules()
  if (projectsStore.projects.length === 0) {
    projectsStore.fetchProjects()
  }
})
</script>
