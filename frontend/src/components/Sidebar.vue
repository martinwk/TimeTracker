<script setup>
import { ref } from 'vue'
import api from '@/api/api'
import { useActivityBlocksStore } from '@/stores/activityBlocks'

defineProps({
  isOpen: Boolean,
});

const emit = defineEmits(['toggle']);

const navItems = [
  { name: 'Dashboard', path: '/' },
  { name: 'Weekstaat', path: '/weekstaat' },
  { name: 'Projects', path: '/projects' },
  { name: 'Stats', path: '/stats' },
];

const store = useActivityBlocksStore()

const syncing = ref(false)
const syncResult = ref(null)  // { blocksCreated, daysCount } | null
const syncError = ref(null)   // string | null

const sync = async () => {
  syncing.value = true
  syncResult.value = null
  syncError.value = null
  try {
    const { data } = await api.post('/activities/sync/', {})
    syncResult.value = {
      blocksCreated: data.blocks_created,
      daysCount: data.days_aggregated.length,
    }
    await store.fetchWeekBlocks()
  } catch (err) {
    if (err?.response?.status === 404) {
      syncError.value = 'Logbestand niet gevonden'
    } else {
      syncError.value = 'Fout bij synchroniseren'
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
      <h1 class="text-xl font-bold hidden md:block">Tijdregistratie</h1>
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
      <button
        data-testid="sync-button"
        @click="sync"
        :disabled="syncing"
        class="flex items-center gap-2 w-full px-3 py-2 text-sm rounded-lg text-gray-600 hover:bg-gray-100 disabled:opacity-40 transition-colors"
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

      <p v-if="syncResult" class="mt-1 text-xs text-green-600 px-1">
        {{ syncResult.blocksCreated }} nieuwe blokken, {{ syncResult.daysCount }} dag(en)
      </p>
      <p v-if="syncError" class="mt-1 text-xs text-red-500 px-1">
        {{ syncError }}
      </p>
    </div>
  </aside>
</template>