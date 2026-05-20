<template>
  <div class="p-6 max-w-5xl mx-auto">

    <!-- Header: weeknavigatie + label -->
    <div class="flex items-center gap-3 mb-6">
      <button
        data-testid="btn-vorige-week"
        @click="store.goToPrevWeek()"
        class="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
        title="Vorige week"
      >
        <svg class="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <h2 class="text-sm font-semibold text-gray-700 w-52 text-center">{{ weekLabel }}</h2>

      <button
        data-testid="btn-volgende-week"
        @click="store.goToNextWeek()"
        class="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
        title="Volgende week"
      >
        <svg class="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>

    <!-- Lege-week melding -->
    <div
      v-if="store.blocks.length === 0"
      data-testid="leeg-melding"
      class="flex flex-col items-center justify-center py-16 text-gray-400"
    >
      <span class="text-4xl mb-3">📭</span>
      <p class="text-sm">Geen activiteit deze week.</p>
    </div>

    <!-- Tabel -->
    <div v-else class="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-200">
            <th class="text-left px-4 py-3 font-medium text-gray-500 min-w-36">Project</th>
            <th
              v-for="day in weekDays"
              :key="day.iso"
              data-testid="dag-header"
              class="text-center px-3 py-3 font-medium text-gray-500 w-20"
              :class="day.isWeekend ? 'bg-gray-100/70' : ''"
            >
              <div class="text-xs uppercase tracking-wide">{{ day.weekdag }}</div>
              <div class="text-base font-semibold text-gray-700">{{ day.dag }}</div>
            </th>
            <th class="text-center px-3 py-3 font-medium text-gray-500 w-20">Totaal</th>
          </tr>
        </thead>

        <tbody>
          <!-- Projectrijen -->
          <tr
            v-for="project in actieveProjecten"
            :key="project.id"
            data-testid="project-rij"
            class="border-b border-gray-100 hover:bg-gray-50 transition-colors"
          >
            <td class="px-4 py-2.5 font-medium text-gray-700">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" :style="{ backgroundColor: project.color }" />
                {{ project.name }}
              </div>
            </td>
            <td
              v-for="day in weekDays"
              :key="day.iso"
              class="text-center px-3 py-2.5"
              :class="day.isWeekend ? 'bg-gray-50/60' : ''"
            >
              <span
                v-if="matrix[project.id]?.[day.iso]"
                class="text-gray-700 tabular-nums"
              >{{ formatUren(matrix[project.id][day.iso]) }}</span>
              <span
                v-else
                data-testid="cel-leeg"
                class="text-gray-300"
              >–</span>
            </td>
            <td data-testid="rij-totaal" class="text-center px-3 py-2.5 font-semibold text-gray-700 tabular-nums">
              {{ formatUren(rijTotaal(project.id)) }}
            </td>
          </tr>

          <!-- Niet-toegewezen rij -->
          <tr
            v-if="heeftNietToegewezen"
            data-testid="rij-niet-toegewezen"
            class="border-b border-gray-100 hover:bg-gray-50 transition-colors"
          >
            <td class="px-4 py-2.5 font-medium text-gray-400 italic">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full flex-shrink-0 bg-gray-200" />
                Niet toegewezen
              </div>
            </td>
            <td
              v-for="day in weekDays"
              :key="day.iso"
              class="text-center px-3 py-2.5"
              :class="day.isWeekend ? 'bg-gray-50/60' : ''"
            >
              <span
                v-if="matrix['onbekend']?.[day.iso]"
                class="text-gray-400 tabular-nums"
              >{{ formatUren(matrix['onbekend'][day.iso]) }}</span>
              <span v-else data-testid="cel-leeg" class="text-gray-300">–</span>
            </td>
            <td class="text-center px-3 py-2.5 font-semibold text-gray-400 tabular-nums">
              {{ formatUren(rijTotaal('onbekend')) }}
            </td>
          </tr>
        </tbody>

        <!-- Totaalrij -->
        <tfoot>
          <tr class="bg-gray-50 border-t-2 border-gray-200">
            <td class="px-4 py-2.5 font-semibold text-gray-700">Totaal</td>
            <td
              v-for="day in weekDays"
              :key="day.iso"
              data-testid="kolom-totaal"
              class="text-center px-3 py-2.5 font-semibold text-gray-700 tabular-nums"
              :class="day.isWeekend ? 'bg-gray-100/70' : ''"
            >
              <span v-if="dagTotaal(day.iso)">{{ formatUren(dagTotaal(day.iso)) }}</span>
              <span v-else class="text-gray-300 font-normal">–</span>
            </td>
            <td data-testid="eindtotaal" class="text-center px-3 py-2.5 font-bold text-gray-900 tabular-nums">
              {{ formatUren(weekTotaal) }}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>

  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'
import { toLocalDateStr, parseLocalDate, getWeekNumber } from '@/utils/date'

const store = useActivityBlocksStore()

// ── Weekdagen ──────────────────────────────────────────────────────────────
const WEEKDAGEN = ['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo']

const weekDays = computed(() => {
  const monday = parseLocalDate(store.currentDate)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(d.getDate() + i)
    const iso = toLocalDateStr(d.toISOString())
    return { iso, weekdag: WEEKDAGEN[i], dag: d.getDate(), isWeekend: i >= 5 }
  })
})

const weekLabel = computed(() => {
  const monday = parseLocalDate(store.currentDate)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)

  const weekNr = getWeekNumber(monday)
  const fmtDay  = (d) => d.toLocaleDateString('nl-NL', { day: 'numeric' })
  const fmtFull = (d) => d.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short' })
  const sameMon = monday.getMonth() === sunday.getMonth()
  const range   = sameMon
    ? `${fmtDay(monday)}–${fmtFull(sunday)}`
    : `${fmtFull(monday)} – ${fmtFull(sunday)}`
  return `Week ${weekNr} · ${range}`
})

// ── Matrix opbouwen ────────────────────────────────────────────────────────
// { projectId | 'onbekend': { 'YYYY-MM-DD': seconds } }
const matrix = computed(() => {
  const m = {}
  for (const block of store.blocks) {
    const day = toLocalDateStr(block.started_at)
    const key = block.project?.id ?? 'onbekend'
    if (!m[key]) m[key] = {}
    m[key][day] = (m[key][day] ?? 0) + block.total_seconds
  }
  return m
})

// Projecten die deze week voorkomen, in volgorde van store.projects
const actieveProjecten = computed(() => {
  const gezien = new Set(
    store.blocks.filter(b => b.project).map(b => b.project.id)
  )
  return store.projects.filter(p => gezien.has(p.id))
})

const heeftNietToegewezen = computed(() =>
  store.blocks.some(b => !b.project)
)

// ── Totaalberekeningen ────────────────────────────────────────────────────
const rijTotaal = (key) =>
  Object.values(matrix.value[key] ?? {}).reduce((s, v) => s + v, 0)

const dagTotaal = (iso) =>
  Object.values(matrix.value).reduce((s, dagMap) => s + (dagMap[iso] ?? 0), 0)

const weekTotaal = computed(() =>
  store.blocks.reduce((s, b) => s + b.total_seconds, 0)
)

// ── Opmaak ────────────────────────────────────────────────────────────────
const formatUren = (seconds) => {
  if (!seconds) return '–'
  const h = seconds / 3600
  const decimaal = parseFloat(h.toFixed(1))
  return decimaal % 1 === 0
    ? `${decimaal}u`
    : `${String(decimaal).replace('.', ',')}u`
}

onMounted(() => store.fetchWeekBlocks())
</script>
