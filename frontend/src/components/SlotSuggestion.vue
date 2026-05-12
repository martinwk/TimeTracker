<template>
    <div class="slot-suggestion absolute z-50 bg-white rounded-xl shadow-xl border border-gray-100 w-56 p-3"
        :style="position" @click.stop>

    <div class="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-2">
      {{ timeLabel }} · Nieuw blok
    </div>

    <!-- Suggestie -->
    <div class="mb-3">
      <div class="text-[11px] text-gray-400 mb-1">Suggestie</div>
            <button v-for="suggestion in suggestions" :key="suggestion.id"
                @click="() => { emit('create', { projectId: suggestion.id, slotInfo }) }"
                class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 transition-colors text-left mb-1">

        <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ backgroundColor: suggestion.color }" />
        <span class="text-sm text-gray-700 font-medium truncate">{{ suggestion.name }}</span>
        <span class="ml-auto text-[10px] text-gray-300">→</span>
      </button>
    </div>

    <!-- Alle projecten -->
    <div class="border-t border-gray-100 pt-2">
      <div class="text-[11px] text-gray-400 mb-1">Ander project</div>
      <button
        v-for="project in otherProjects"
        :key="project.id"
        @click="() => { emit('create', { projectId: project.id, slotInfo }) }"
        class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 transition-colors text-left"
      >
        <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ backgroundColor: project.color }" />
        <span class="text-sm text-gray-600 truncate">{{ project.name }}</span>
      </button>
    </div>

    <!-- Annuleren -->
    <button
      @click="emit('close')"
      class="mt-2 w-full text-center text-xs text-gray-300 hover:text-gray-500 transition-colors"
    >
      Annuleren
    </button>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'

const props = defineProps({
  slotInfo: { type: Object, required: true }, // { iso, hour, minute }
  position: { type: Object, required: true },  // { top, left }
})

const emit = defineEmits(['create', 'close'])
const store = useActivityBlocksStore()

const timeLabel = computed(() => {
  const h = String(props.slotInfo.hour).padStart(2, '0')
  const m = String(props.slotInfo.minute).padStart(2, '0')
  return `${h}:${m}`
})

// Mock suggestie: gewoon het eerste project als "suggestie"
const suggestions = computed(() => store.projects.slice(0, 1))
const otherProjects = computed(() => store.projects.slice(1))

</script>
