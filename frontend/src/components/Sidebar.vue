<script setup>
import { ref } from 'vue'
import api from '@/api/api'
import { useActivityBlocksStore } from '@/stores/activityBlocks'
import SettingsPanel from './SettingsPanel.vue'

defineProps({
  isOpen: Boolean,
});

const emit = defineEmits(['toggle']);

const navItems = [
  { name: 'Dashboard', path: '/' },
  { name: 'Weekstaat', path: '/weekstaat' },
  { name: 'Projects', path: '/projects' },
  { name: 'Stats', path: '/stats' },
  { name: 'Regels', path: '/rules' },
];

const store = useActivityBlocksStore()

const syncing = ref(false)
const syncResult = ref(null)  // { blocksCreated, daysCount } | null
const syncError = ref(null)   // string | null
const settingsOpen = ref(false)

const sync = async () => {
  syncing.value = true
  syncResult.value = null
  syncError.value = null
  try {
    const logPath = localStorage.getItem('ahk_log_path')
    const body = logPath ? { log_path: logPath } : {}
    // Langere timeout: sync importeert een logbestand en herberekent alle betrokken dagen
    const { data } = await api.post('/activities/sync/', body, { timeout: 60000 })
    syncResult.value = {
      blocksCreated: data.blocks_created,
      daysCount: data.days_aggregated.length,
    }
    await store.fetchWeekBlocks()
  } catch (err) {
    const detail = err?.response?.data?.error ?? err?.response?.data?.detail
    if (err?.response?.status === 404) {
      syncError.value = detail ?? 'Logbestand niet gevonden'
    } else {
      syncError.value = detail ?? `Fout bij synchroniseren (${err?.response?.status ?? 'netwerk'})`
    }
  } finally {
    syncing.value = false
  }
}
</script>

<template>
  <aside
    class="fixed left-0 top-0 h-full w-64 bg-white shadow-md transform transition-transform duration-300 ease-in-out"
    :class="isOpen ? 'translate-x-0' : '-translate-x-full'"
  >
    <div class="p-4 border-b">
      <button
        @click="emit('toggle')"
        class="p-2 rounded-md hover:bg-gray-100 md:hidden"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
      <div class="text-xl font-bold hidden md:block truncate">Tijdregistratie</div>
    </div>

    <nav class="p-4">
      <ul class="space-y-2">
        <li v-for="item in navItems" :key="item.path">
          <router-link
            :to="item.path"
            class="flex items-center p-2 rounded-md hover:bg-gray-100"
            active-class="bg-blue-50 text-blue-600"
          >
            {{ item.name }}
          </router-link>
        </li>
      </ul>
    </nav>

    <div class="p-4 border-t mt-auto absolute bottom-0 w-full">
      <!-- Settings panel (rendered above the bottom bar) -->
      <SettingsPanel :is-open="settingsOpen" @close="settingsOpen = false" />

      <div class="flex items-center gap-1">
        <button
          data-testid="sync-button"
          @click="sync"
          :disabled="syncing"
          class="flex items-center gap-2 flex-1 px-3 py-2 text-sm rounded-lg text-gray-600 hover:bg-gray-100 disabled:opacity-40 transition-colors"
        >
          <svg
            class="w-4 h-4 flex-shrink-0"
            :class="{ 'animate-spin': syncing }"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Synchroniseren
        </button>

        <button
          data-testid="settings-button"
          @click="settingsOpen = !settingsOpen"
          class="p-2 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
          :class="{ 'bg-gray-100 text-gray-700': settingsOpen }"
          aria-label="Instellingen"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>

      <p v-if="syncResult" class="mt-1 text-xs text-green-600 px-1">
        {{ syncResult.blocksCreated }} nieuwe blokken, {{ syncResult.daysCount }} dag(en)
      </p>
      <p v-if="syncError" class="mt-1 text-xs text-red-500 px-1">
        {{ syncError }}
      </p>
    </div>
  </aside>
</template>
