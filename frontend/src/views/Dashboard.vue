<template>
  <div class="p-6 max-w-full">

    <!-- Header -->
    <div class="flex flex-wrap items-center gap-4 mb-5">

      <!-- Week navigatie -->
      <div class="flex items-center gap-2">
        <button
          @click="store.goToPrevWeek()"
          :disabled="isLoading"
          class="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 transition-colors"
          title="Vorige week"
        >
          <svg class="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <VueDatePicker
          v-model="pickerDate"
          :enable-time-picker="false"
          auto-apply
          week-picker
          :week-picker-start-day="1"
          :locale="nl"
          :format="formatWeekLabel"
          :disabled="isLoading"
          class="w-56"
          @update:model-value="onPickerChange"
        />

        <button
          @click="store.goToNextWeek()"
          :disabled="isLoading"
          class="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 transition-colors"
          title="Volgende week"
        >
          <svg class="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      <!-- Acties -->
      <div class="flex items-center gap-2 flex-wrap">
        <button
          v-if="unassignedBlocks.length > 0"
          @click="store.selectUnassigned()"
          :disabled="isLoading"
          class="px-3 py-1.5 text-xs font-medium rounded-lg bg-orange-50 text-orange-600 border border-orange-200 hover:bg-orange-100 disabled:opacity-40 transition-colors"
        >
          Ongekoppeld ({{ unassignedBlocks.length }})
        </button>

        <button
          v-if="blocks.length > 0"
          @click="store.selectAll()"
          :disabled="isLoading"
          class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 transition-colors"
        >
          Alles selecteren
        </button>

        <button
          v-if="selectedBlocks.length > 0"
          @click="store.clearSelection()"
          class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
        >
          Wis selectie ({{ selectedBlocks.length }})
        </button>

        <button
          v-if="selectedBlocks.length > 0"
          @click="showProjectSelector = true"
          class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
        >
          Toewijzen aan project →
        </button>

        <button
          @click="store.applyRules()"
          :disabled="isLoading || unassignedBlocks.length === 0"
          class="px-3 py-1.5 text-xs font-medium rounded-lg bg-green-50 text-green-600 border border-green-200 hover:bg-green-100 disabled:opacity-40 transition-colors"
        >
          ⚡ Auto-toewijzen
        </button>
      </div>

      <!-- Laad indicator -->
      <div v-if="isLoading" class="ml-auto flex items-center gap-2 text-xs text-gray-400">
        <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        Laden...
      </div>
    </div>

    <!-- Foutmelding -->
    <div v-if="error" class="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-600 text-sm border border-red-100">
      {{ error }}
    </div>

    <!-- Legenda projecten -->
    <div v-if="projects.length > 0" class="flex flex-wrap gap-3 mb-4">
      <div
        v-for="project in projects"
        :key="project.id"
        class="flex items-center gap-1.5 text-xs text-gray-500"
      >
        <span class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: project.color }" />
        {{ project.name }}
      </div>
      <div class="flex items-center gap-1.5 text-xs text-gray-400">
        <span class="w-2.5 h-2.5 rounded-full bg-gray-200" />
        Ongekoppeld
      </div>
    </div>

    <!-- Weekgrid -->
    <ActivityBlockGrid />

    <!-- Project selector modal -->
    <ProjectSelector
      v-if="showProjectSelector"
      @close="showProjectSelector = false"
      @assign="handleAssign"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { nl } from 'date-fns/locale'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import { useActivityBlocksStore } from '@/stores/activityBlocks'
import ActivityBlockGrid from '@/components/ActivityBlockGrid.vue'
import ProjectSelector from '@/components/ProjectSelector.vue'

const store = useActivityBlocksStore()
const showProjectSelector = ref(false)

const blocks = computed(() => store.blocks)
const selectedBlocks = computed(() => store.selectedBlocks)
const unassignedBlocks = computed(() => store.unassignedBlocks)
const projects = computed(() => store.projects)
const isLoading = computed(() => store.isLoading)
const error = computed(() => store.error)

// VueDatePicker week-picker verwacht [maandag, zondag]
const pickerDate = computed({
  get: () => {
    const monday = new Date(store.currentDate)
    const sunday = new Date(monday)
    sunday.setDate(monday.getDate() + 6)
    return [monday, sunday]
  },
  set: () => {},
})

const onPickerChange = (val) => {
  // week-picker geeft een array [maandag, zondag] terug
  const monday = Array.isArray(val) ? val[0] : val
  if (!monday) return
  store.currentDate = new Date(monday).toISOString().split('T')[0]
  store.fetchWeekBlocks()
}

const formatWeekLabel = (dates) => {
  const start = Array.isArray(dates) ? dates[0] : dates
  if (!start) return ''
  const d   = new Date(start)
  const end = new Date(d)
  end.setDate(d.getDate() + 6)

  const week     = getWeekNumber(d)
  const fmtDay   = (date) => date.toLocaleDateString('nl-NL', { day: 'numeric' })
  const fmtFull  = (date) => date.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short' })
  const sameMon  = d.getMonth() === end.getMonth()

  // "Week 20 · 12–18 mei" als zelfde maand, anders "12 apr – 2 mei"
  const range = sameMon
    ? `${fmtDay(d)}–${fmtFull(end)}`
    : `${fmtFull(d)} – ${fmtFull(end)}`
  return `Week ${week} · ${range}`
}

const getWeekNumber = (date) => {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7))
  const yearStart = new Date(d.getFullYear(), 0, 4)
  return Math.ceil((((d - yearStart) / 86400000) + 1) / 7)
}

const handleAssign = (projectId) => {
  store.assignToProject(projectId)
  showProjectSelector.value = false
}

onMounted(() => store.fetchWeekBlocks())
</script>
