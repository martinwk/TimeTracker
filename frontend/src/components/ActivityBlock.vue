<template>
  <div
    class="activity-block absolute left-0.5 right-0.5 rounded overflow-visible select-none transition-colors duration-100"
    :class="[
      isSelected
        ? 'ring-2 ring-blue-500 ring-offset-1 z-20'
        : 'hover:ring-1 hover:ring-blue-300 hover:z-10 z-0',
      isDragging ? 'opacity-40 pointer-events-none' : '',
    ]"
    :style="[style, { cursor: activeCursor }]"
    :title="displayTitle"
    @mousedown.stop="onMouseDown"
    @mousemove="onMouseMove"
    @mouseleave="onMouseLeave"
  >
    <!-- Project kleurstreep links -->
    <div
      v-if="project"
      class="absolute left-0 top-0 bottom-0 w-1 shrink-0 rounded-l"
      :style="{ backgroundColor: project.color }"
    />

    <!-- Resize-handle boven -->
    <div
      class="absolute inset-x-0 top-0 h-2 z-10 flex items-start justify-center pt-px pointer-events-none transition-opacity duration-100"
      :class="nearEdge === 'top' ? 'opacity-100' : 'opacity-0'"
    >
      <div class="w-5 h-0.5 rounded-full bg-blue-400" />
    </div>

    <!-- Inhoud -->
    <div class="absolute inset-0 flex flex-col justify-between p-0.5 pl-1.5 overflow-hidden rounded">
      <span
        v-if="isLargeEnough"
        class="text-[10px] leading-tight font-medium truncate"
        :class="project ? 'text-gray-800' : 'text-gray-500'"
      >
        {{ displayTitle }}
      </span>
      <div class="flex items-center justify-end gap-1">
        <span v-if="props.blocks && props.blocks.length > 1" class="text-[9px] text-gray-300">
          {{ props.blocks.length }}×
        </span>
        <span class="text-[9px] leading-none text-gray-400">
          {{ formatDuration(totalSeconds) }}
        </span>
      </div>
    </div>

    <!-- Resize-handle onder -->
    <div
      class="absolute inset-x-0 bottom-0 h-2 z-10 flex items-end justify-center pb-px pointer-events-none transition-opacity duration-100"
      :class="nearEdge === 'bottom' ? 'opacity-100' : 'opacity-0'"
    >
      <div class="w-5 h-0.5 rounded-full bg-blue-400" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { parseLocalDate } from '@/utils/date'

// Pixels van boven/onder die als resize-zone gelden
const EDGE_PX = 7

const props = defineProps({
  blocks:     { type: Array,   required: true },
  isSelected: { type: Boolean, default: false },
  isDragging: { type: Boolean, default: false },
  hourHeight: { type: Number,  required: true },
})

const emit = defineEmits(['move-start', 'resize-start'])

// ── Derived data ───────────────────────────────────────────────────────────────
const isMerged     = computed(() => props.blocks.length > 1)
const primaryBlock = computed(() => props.blocks[0])
const project      = computed(() => primaryBlock.value?.project ?? null)
const displayTitle = computed(() => project.value?.name ?? primaryBlock.value?.dominant_title ?? '')
const totalSeconds = computed(() => props.blocks.reduce((s, b) => s + b.total_seconds, 0))

// ── Positie / stijl ────────────────────────────────────────────────────────────

// Visuele duur in minuten: gebruik ended_at (werkelijke tijdspanne, incl. pauzes
// tussen AHK-activiteiten), val terug op total_seconds voor tijdelijke blokken.
const visualDurationMin = computed(() => {
  const first           = primaryBlock.value
  const start           = parseLocalDate(first.started_at)
  const minFromMidnight = start.getHours() * 60 + start.getMinutes()

  let endMin
  if (isMerged.value) {
    const last = props.blocks[props.blocks.length - 1]
    if (last.ended_at) {
      const e = parseLocalDate(last.ended_at)
      endMin  = e.getHours() * 60 + e.getMinutes()
    } else {
      const ls = parseLocalDate(last.started_at)
      endMin   = ls.getHours() * 60 + ls.getMinutes() + last.total_seconds / 60
    }
  } else {
    const block = props.blocks[0]
    if (block.ended_at) {
      const e = parseLocalDate(block.ended_at)
      endMin  = e.getHours() * 60 + e.getMinutes()
    } else {
      endMin = minFromMidnight + block.total_seconds / 60
    }
  }

  // Bescherming bij midnight-overgang (ended_at op volgende dag)
  if (endMin <= minFromMidnight) endMin = minFromMidnight + totalSeconds.value / 60
  return endMin - minFromMidnight
})

const style = computed(() => {
  const first           = primaryBlock.value
  const start           = parseLocalDate(first.started_at)
  const minFromMidnight = start.getHours() * 60 + start.getMinutes()
  const top             = (minFromMidnight / 60) * props.hourHeight
  const height          = Math.max((visualDurationMin.value / 60) * props.hourHeight, 12)
  const bg              = project.value ? project.value.color + '28' : '#f1f5f9'
  return { top: top + 'px', height: height + 'px', backgroundColor: bg }
})

const isLargeEnough = computed(() => {
  return (visualDurationMin.value / 60) * props.hourHeight >= 22
})

// ── Cursor / edge detection ────────────────────────────────────────────────────
const nearEdge = ref(null) // 'top' | 'bottom' | null

const getEdge = (event) => {
  const rect = event.currentTarget.getBoundingClientRect()
  const y    = event.clientY - rect.top
  if (y <= EDGE_PX)               return 'top'
  if (y >= rect.height - EDGE_PX) return 'bottom'
  return null
}

const activeCursor = computed(() => nearEdge.value ? 'ns-resize' : 'grab')

const onMouseMove  = (e) => { nearEdge.value = getEdge(e) }
const onMouseLeave = ()  => { nearEdge.value = null }

// ── Mousedown — delegeer naar grid ────────────────────────────────────────────
const onMouseDown = (event) => {
  if (event.button !== 0) return
  const edge = getEdge(event)
  if (edge) {
    emit('resize-start', { event, blocks: props.blocks, edge })
  } else {
    emit('move-start', { event, blocks: props.blocks })
  }
}

// ── Utils ──────────────────────────────────────────────────────────────────────
const formatDuration = (seconds) => {
  const m   = Math.floor(seconds / 60)
  if (m < 60) return `${m}m`
  const h   = Math.floor(m / 60)
  const rem = m % 60
  return rem > 0 ? `${h}u${rem}m` : `${h}u`
}
</script>
