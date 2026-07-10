<template>
  <!-- Backdrop -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
    @click.self="handleClose"
  >
    <div class="bg-white rounded-2xl shadow-xl w-80 overflow-hidden">

      <!-- Header -->
      <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h2 class="text-sm font-semibold text-gray-800">Project toewijzen</h2>
          <p class="text-xs text-gray-400 mt-0.5">{{ selectedCount }} blok{{ selectedCount !== 1 ? 'ken' : '' }} geselecteerd</p>
        </div>
        <button
          data-action="sluiten"
          @click="handleClose"
          class="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Zoekbalk -->
      <div class="px-5 pt-3 pb-1">
        <input
          ref="searchInput"
          v-model="searchQuery"
          type="text"
          placeholder="Zoeken..."
          class="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400 placeholder-gray-300"
        />
      </div>

      <!-- Projecten lijst -->
      <ul class="py-2">
        <li
          v-for="project in filteredProjects"
          :key="project.id"
          class="project-item flex items-center gap-3 px-5 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
          @click="emit('assign', project.id)"
        >
          <span
            class="w-3 h-3 rounded-full shrink-0"
            :style="{ backgroundColor: project.color }"
          />
          <span class="text-sm text-gray-700 font-medium">{{ project.name }}</span>
        </li>
        <li v-if="filteredProjects.length === 0" class="px-5 py-3">
          <p class="text-sm text-gray-400">Geen projecten gevonden</p>
        </li>
      </ul>

      <!-- Geen koppeling optie -->
      <div class="border-t border-gray-100 px-5 py-3">
        <button
          @click="emit('assign', null)"
          class="w-full flex items-center justify-between text-xs text-gray-400 hover:text-gray-600 transition-colors text-left"
        >
          <span>Koppeling verwijderen</span>
          <span class="text-[10px] text-gray-300">(d)</span>
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'

const store = useActivityBlocksStore()
const selectedCount = computed(() => store.selectedBlocks.length)

const emit = defineEmits(['close', 'assign'])

const searchQuery = ref('')
const searchInput = ref(null)

const handleClose = () => {
  searchQuery.value = ''
  emit('close')
}

const filteredProjects = computed(() => {
  if (!searchQuery.value) return store.projects
  const q = searchQuery.value.toLowerCase()
  return store.projects.filter(p => p.name.toLowerCase().includes(q))
})

const onKeyDown = (e) => {
  // Suppress shortcuts when the search field is focused
  if (e.target === searchInput.value) return
  if (e.key === 'Escape') handleClose()
  if (e.key === 'd' || e.key === 'Delete') emit('assign', null)
}
onMounted(() => {
  document.addEventListener('keydown', onKeyDown)
  nextTick(() => searchInput.value?.focus())
})
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))
</script>
