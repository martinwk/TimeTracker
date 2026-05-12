<template>
  <div
    class="absolute left-0.5 right-0.5 rounded overflow-hidden cursor-pointer transition-all duration-100"
    :class="[
      isSelected
        ? 'ring-2 ring-blue-500 ring-offset-1 z-20'
        : 'hover:ring-1 hover:ring-blue-300 hover:z-10 z-0',
    ]"
    :style="style"
    @click.stop="onToggle"
    :title="displayTitle"
  >
    <!-- Project kleurstreep links -->
    <div
      v-if="project"
      class="absolute left-0 top-0 bottom-0 w-1 shrink-0"
      :style="{ backgroundColor: project.color }"
    />

    <!-- Inhoud -->
    <div class="absolute inset-0 flex flex-col justify-between p-0.5 pl-1.5 overflow-hidden">
      <span
        v-if="isLargeEnough"
        class="text-[10px] leading-tight font-medium truncate"
        :class="project ? 'text-gray-800' : 'text-gray-500'"
      >
        {{ displayTitle }}
      </span>
      <div class="flex items-center justify-end gap-1">
        <span v-if="props.blocks && props.blocks.length > 1" class="text-[9px] text-gray-300">{{ props.blocks.length }}×</span>
        <span class="text-[9px] leading-none text-gray-400">
          {{ formatDuration(totalSeconds) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { parseLocalDate } from '@/utils/date'

const props = defineProps({
  // Enkelvoudig blok (backwards compat) of samengevoegd blok
  block: { type: Object, default: null },
  // Samengevoegde blokken — als dit meegegeven wordt, is het een merged blok
  blocks: { type: Array, default: null },
  isSelected: { type: Boolean, default: false },
  hourHeight: { type: Number, required: true },
})

const emit = defineEmits(['toggle', 'toggleMany'])

// Gebruik blocks array als aanwezig, anders enkelvoudig block
const isMerged = computed(() => !!props.blocks && props.blocks.length > 1)
const primaryBlock = computed(() =>
  props.blocks ? props.blocks[0] : props.block
)
const project = computed(() => primaryBlock.value?.project ?? null)
const displayTitle = computed(() => project.value?.name ?? primaryBlock.value?.dominant_title ?? '')
const totalSeconds = computed(() =>
  props.blocks
    ? props.blocks.reduce((sum, b) => sum + b.total_seconds, 0)
    : props.block.total_seconds
)

// Positie en hoogte op basis van eerste en laatste blok
const style = computed(() => {
  const first = primaryBlock.value
  const start = parseLocalDate(first.started_at)
  const minutesFromMidnight = start.getHours() * 60 + start.getMinutes()
  const top = (minutesFromMidnight / 60) * props.hourHeight

  let durationMin
  if (isMerged.value) {
    const last = props.blocks[props.blocks.length - 1]
    const lastStart = parseLocalDate(last.started_at)
    const lastMinutes = lastStart.getHours() * 60 + lastStart.getMinutes()
    durationMin = lastMinutes + last.total_seconds / 60 - minutesFromMidnight
  } else {
    durationMin = totalSeconds.value / 60
  }

  const height = Math.max((durationMin / 60) * props.hourHeight, 12)
  const bg = project.value ? project.value.color + '28' : '#f1f5f9'

  return {
    top: top + 'px',
    height: height + 'px',
    backgroundColor: bg,
  }
})

const isLargeEnough = computed(() => {
  const durationMin = totalSeconds.value / 60
  return (durationMin / 60) * props.hourHeight >= 22
})

const onToggle = () => {
  if (props.blocks) {
    emit('toggleMany', props.blocks.map(b => b.id))
  } else {
    emit('toggle', props.block.id)
  }
}

const formatDuration = (seconds) => {
  const m = Math.floor(seconds / 60)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  const rem = m % 60
  return rem > 0 ? `${h}u${rem}m` : `${h}u`
}
</script>
