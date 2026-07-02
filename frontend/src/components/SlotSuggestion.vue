<template>
    <div class="slot-suggestion absolute z-50 bg-white rounded-xl shadow-xl border border-gray-100 w-56 p-3"
        :style="position" @click.stop>

    <div class="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-2">
      {{ timeLabel }} · {{ title }}
    </div>

    <!-- Activiteiten uit AHK-import -->
    <div v-if="activities.length > 0" class="mb-3">
      <div class="text-[11px] text-gray-400 mb-1">Activiteiten</div>
      <div
        v-for="act in activities"
        :key="act.title"
        class="flex items-center gap-1 py-0.5"
      >
        <span class="text-[11px] text-gray-600 truncate flex-1">{{ act.title }}</span>
        <span class="text-[10px] text-gray-400 shrink-0">{{ formatDuration(act.seconds) }}</span>
      </div>
      <div class="flex justify-between items-center mt-1.5 pt-1 border-t border-gray-100 text-[10px] text-gray-400">
        <span>actief</span>
        <span>{{ formatDuration(totalActiveSeconds) }} / {{ formatDuration(wallClockSeconds) }}</span>
      </div>
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

    <!-- Koppeling verwijderen -->
    <div v-if="canUnassign" class="border-t border-gray-100 pt-2 mt-1">
      <button
        @click="emit('create', { projectId: null, slotInfo })"
        class="w-full flex items-center justify-between text-xs text-red-400 hover:text-red-600 transition-colors px-2 py-1"
      >
        <span>Koppeling verwijderen</span>
        <span class="text-[10px] text-gray-300 ml-2">(d)</span>
      </button>
    </div>

    <!-- Annuleren -->
    <button
      @click="emit('close')"
      class="mt-2 w-full flex items-center justify-center gap-1.5 text-xs text-gray-300 hover:text-gray-500 transition-colors"
    >
      <span>Annuleren</span>
      <span class="text-[10px]">(Esc)</span>
    </button>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'
import { formatDuration } from '@/utils/date'

const props = defineProps({
  slotInfo:         { type: Object,  required: true },
  position:         { type: Object,  required: true },
  activities:       { type: Array,   default: () => [] }, // [{ title, seconds }]
  title:            { type: String,  default: 'Nieuw blok' },
  canUnassign:      { type: Boolean, default: false },
  wallClockSeconds: { type: Number,  default: 900 },
})

const emit = defineEmits(['create', 'close'])
const store = useActivityBlocksStore()

const onKeyDown = (e) => {
  if (e.key === 'Escape') emit('close')
  if ((e.key === 'd' || e.key === 'Delete') && props.canUnassign) {
    emit('create', { projectId: null, slotInfo: props.slotInfo })
  }
}
onMounted(() => document.addEventListener('keydown', onKeyDown))
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))

const timeLabel = computed(() => {
  const h = String(props.slotInfo.hour).padStart(2, '0')
  const m = String(props.slotInfo.minute).padStart(2, '0')
  return `${h}:${m}`
})

const totalActiveSeconds = computed(() =>
  props.activities.reduce((s, a) => s + a.seconds, 0)
)

// Mock suggestie: gewoon het eerste project als "suggestie"
const suggestions   = computed(() => store.projects.slice(0, 1))
const otherProjects = computed(() => store.projects.slice(1))
</script>
