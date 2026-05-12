<template>
  <!-- Backdrop -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
    @click.self="emit('close')"
  >
    <div class="bg-white rounded-2xl shadow-xl w-80 overflow-hidden">

      <!-- Header -->
      <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h2 class="text-sm font-semibold text-gray-800">Project toewijzen</h2>
          <p class="text-xs text-gray-400 mt-0.5">{{ selectedCount }} blok{{ selectedCount !== 1 ? 'ken' : '' }} geselecteerd</p>
        </div>
        <button
          @click="emit('close')"
          class="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Projecten lijst -->
      <ul class="py-2">
        <li
          v-for="project in projects"
          :key="project.id"
          @click="emit('assign', project.id)"
          class="flex items-center gap-3 px-5 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
        >
          <span
            class="w-3 h-3 rounded-full shrink-0"
            :style="{ backgroundColor: project.color }"
          />
          <span class="text-sm text-gray-700 font-medium">{{ project.name }}</span>
        </li>
      </ul>

      <!-- Geen koppeling optie -->
      <div class="border-t border-gray-100 px-5 py-3">
        <button
          @click="emit('assign', null)"
          class="w-full text-xs text-gray-400 hover:text-gray-600 transition-colors text-left"
        >
          Koppeling verwijderen
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'

const store = useActivityBlocksStore()
const projects = computed(() => store.projects)
const selectedCount = computed(() => store.selectedBlocks.length)

const emit = defineEmits(['close', 'assign'])
</script>
