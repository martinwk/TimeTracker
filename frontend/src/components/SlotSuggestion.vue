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

    <!-- Zoekbalk -->
    <div class="mb-2">
      <input
        ref="searchInput"
        v-model="searchQuery"
        type="text"
        placeholder="Zoeken..."
        class="w-full px-2 py-1 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400 placeholder-gray-300"
      />
    </div>

    <!-- Gefilterde projectenlijst (bij actieve zoekopdracht) -->
    <template v-if="searchQuery">
      <div class="mb-1">
        <p v-if="filteredProjects.length === 0" class="text-[11px] text-gray-400 px-2 py-1">
          Geen projecten gevonden
        </p>
        <button
          v-for="project in filteredProjects"
          :key="project.id"
          class="project-item w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 transition-colors text-left"
          @click="() => { emit('create', { projectId: project.id, slotInfo }) }"
        >
          <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ backgroundColor: project.color }" />
          <span class="text-sm text-gray-700 truncate">{{ project.name }}</span>
        </button>
      </div>
    </template>

    <!-- Standaardweergave (geen zoekopdracht): Suggestie + Ander project -->
    <template v-else>
      <!-- Suggestie -->
      <div v-if="suggestions.length > 0" class="mb-3">
        <div class="text-[11px] text-gray-400 mb-1">Suggestie</div>
        <button
          v-for="suggestion in suggestions"
          :key="suggestion.id"
          class="project-item w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 transition-colors text-left mb-1"
          @click="() => { emit('create', { projectId: suggestion.id, slotInfo }) }"
        >
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
          class="project-item w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 transition-colors text-left"
          @click="() => { emit('create', { projectId: project.id, slotInfo }) }"
        >
          <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ backgroundColor: project.color }" />
          <span class="text-sm text-gray-600 truncate">{{ project.name }}</span>
        </button>
      </div>
    </template>

    <!-- Commentaar -->
    <div v-if="blockIds.length > 0" class="mb-2">
      <textarea
        ref="commentInput"
        v-model="commentDraft"
        rows="2"
        placeholder="Notitie..."
        class="w-full px-2 py-1 text-xs border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400 placeholder-gray-300 resize-none"
        @blur="saveCommentIfChanged"
        @keydown.enter.exact.prevent="submitComment"
      />
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
      data-action="annuleren"
      @click="handleClose"
      class="mt-2 w-full flex items-center justify-center gap-1.5 text-xs text-gray-300 hover:text-gray-500 transition-colors"
    >
      <span>Annuleren</span>
      <span class="text-[10px]">(Esc)</span>
    </button>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'
import { formatDuration } from '@/utils/date'

const props = defineProps({
  slotInfo:         { type: Object,  required: true },   // { iso, hour, minute }
  position:         { type: Object,  required: true },   // { top, left }
  activities:       { type: Array,   default: () => [] }, // [{ title, seconds }]
  title:            { type: String,  default: 'Nieuw blok' },
  canUnassign:      { type: Boolean, default: false },
  blockIds:         { type: Array,   default: () => [] },
  initialComment:   { type: String,  default: '' },
  wallClockSeconds: { type: Number,  default: 900 },
})

const emit = defineEmits(['create', 'close'])
const store = useActivityBlocksStore()

const searchQuery  = ref('')
const searchInput  = ref(null)
const commentInput = ref(null)
const commentDraft = ref(props.initialComment)

const handleClose = () => {
  searchQuery.value = ''
  emit('close')
}

const saveCommentIfChanged = () => {
  if (commentDraft.value !== props.initialComment) {
    store.saveComment(props.blockIds, commentDraft.value)
  }
}

const submitComment = () => {
  saveCommentIfChanged()
  handleClose()
}

const onKeyDown = (e) => {
  // Suppress shortcuts when the search field or comment field is focused
  if (e.target === searchInput.value || e.target === commentInput.value) return
  if (e.key === 'Escape') handleClose()
  if ((e.key === 'd' || e.key === 'Delete') && props.canUnassign) {
    emit('create', { projectId: null, slotInfo: props.slotInfo })
  }
}
onMounted(() => {
  document.addEventListener('keydown', onKeyDown)
  nextTick(() => searchInput.value?.focus())
})
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))

// Reset search/comment when popup reopens (position changes signal a new open)
watch(() => props.position, () => { searchQuery.value = '' })
watch(() => props.initialComment, (val) => { commentDraft.value = val })

const timeLabel = computed(() => {
  const h = String(props.slotInfo.hour).padStart(2, '0')
  const m = String(props.slotInfo.minute).padStart(2, '0')
  return `${h}:${m}`
})

const totalActiveSeconds = computed(() =>
  props.activities.reduce((s, a) => s + a.seconds, 0)
)

const filteredProjects = computed(() => {
  if (!searchQuery.value) return store.projects
  const q = searchQuery.value.toLowerCase()
  return store.projects.filter(p => p.name.toLowerCase().includes(q))
})

// Mock suggestie: gewoon het eerste project als "suggestie"
const suggestions   = computed(() => store.projects.slice(0, 1))
const otherProjects = computed(() => store.projects.slice(1))
</script>
