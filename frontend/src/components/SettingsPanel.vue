<script setup>
import { ref } from 'vue'
import api from '@/api/api'
import { parseLocalDate, toLocalDateStr } from '@/utils/date'
import { useActivityBlocksStore } from '@/stores/activityBlocks'

defineProps({
  isOpen: Boolean,
})

const emit = defineEmits(['close'])

const store = useActivityBlocksStore()

// ── Log pad ──────────────────────────────────────────────────────────────────
const logPath = ref(localStorage.getItem('ahk_log_path') ?? '')

const onLogPathInput = (e) => {
  logPath.value = e.target.value
  localStorage.setItem('ahk_log_path', logPath.value)
}

// ── Bestand importeren ───────────────────────────────────────────────────────
const importing = ref(false)
const importResult = ref(null)  // number | null
const importError = ref(null)   // string | null

const onFileChange = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return

  importing.value = true
  importResult.value = null
  importError.value = null

  try {
    const formData = new FormData()
    formData.append('files', file)
    const { data } = await api.post('/activities/import/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    importResult.value = data.imported
    await store.fetchWeekBlocks()
  } catch {
    importError.value = 'Fout bij importeren'
  } finally {
    importing.value = false
  }
}

// ── Regels toepassen ─────────────────────────────────────────────────────────
const applyingRules = ref(false)
const rulesResult = ref(null)   // number | null
const rulesError = ref(null)    // string | null

const applyRules = async () => {
  applyingRules.value = true
  rulesResult.value = null
  rulesError.value = null

  try {
    const dateFrom = store.currentDate
    const dateTo = toLocalDateStr(
      (() => {
        const d = parseLocalDate(dateFrom)
        d.setDate(d.getDate() + 6)
        return d.toISOString()
      })()
    )
    const { data } = await api.post('/activities/apply-rules/', { date_from: dateFrom, date_to: dateTo })
    rulesResult.value = data.blocks_assigned
  } catch {
    rulesError.value = 'Fout bij toepassen van regels'
  } finally {
    applyingRules.value = false
  }
}
</script>

<template>
  <div
    v-if="isOpen"
    data-testid="settings-panel"
    class="absolute bottom-14 left-0 w-64 bg-white border shadow-lg rounded-t-lg p-4 space-y-5 z-10"
  >
    <div class="flex items-center justify-between border-b pb-2">
      <h2 class="text-sm font-semibold text-gray-700">Instellingen</h2>
      <button
        data-testid="close-button"
        @click="emit('close')"
        class="p-1 rounded hover:bg-gray-100 text-gray-500"
        aria-label="Sluiten"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Log pad -->
    <section>
      <label class="block text-xs font-medium text-gray-600 mb-1">Log pad</label>
      <input
        data-testid="log-path-input"
        type="text"
        :value="logPath"
        @input="onLogPathInput"
        placeholder="/pad/naar/window_log.txt"
        class="w-full text-xs border rounded px-2 py-1.5 text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <p class="mt-1 text-xs text-gray-400">Leeg = automatisch detecteren</p>
    </section>

    <!-- Bestand importeren -->
    <section>
      <label class="block text-xs font-medium text-gray-600 mb-1">Bestand importeren</label>
      <label
        class="flex items-center gap-2 w-full px-3 py-1.5 text-xs rounded border border-dashed border-gray-300 text-gray-500 hover:bg-gray-50 cursor-pointer transition-colors"
      >
        <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1M12 12V4m0 0L8 8m4-4l4 4" />
        </svg>
        <span>{{ importing ? 'Bezig…' : 'Kies .txt-bestand' }}</span>
        <input
          data-testid="file-input"
          type="file"
          accept=".txt"
          class="sr-only"
          :disabled="importing"
          @change="onFileChange"
        />
      </label>
      <p v-if="importResult !== null" class="mt-1 text-xs text-green-600">
        Geïmporteerd: {{ importResult }} regels
      </p>
      <p v-if="importError" class="mt-1 text-xs text-red-500">
        {{ importError }}
      </p>
    </section>

    <!-- Regels toepassen -->
    <section>
      <button
        data-testid="apply-rules-button"
        @click="applyRules"
        :disabled="applyingRules"
        class="flex items-center gap-2 w-full px-3 py-1.5 text-xs rounded-lg text-gray-600 hover:bg-gray-100 disabled:opacity-40 transition-colors"
      >
        <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        Regels opnieuw toepassen
      </button>
      <p v-if="rulesResult !== null" class="mt-1 text-xs text-green-600 px-1">
        {{ rulesResult }} blokken toegewezen
      </p>
      <p v-if="rulesError" class="mt-1 text-xs text-red-500 px-1">
        {{ rulesError }}
      </p>
    </section>
  </div>
</template>
