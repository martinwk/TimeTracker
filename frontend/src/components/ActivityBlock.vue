<template>
  <div
    class="absolute left-0.5 right-0.5 rounded overflow-hidden cursor-pointer transition-all duration-100 group"
    :class="[
      isSelected
        ? 'ring-2 ring-blue-500 ring-offset-1 z-20'
        : 'hover:ring-1 hover:ring-blue-300 hover:z-10 z-0',
    ]"
    :style="style"
    @click.stop="emit('toggle', block.id)"
    :title="block.dominant_title"
  >
    <!-- Project kleurstreep links -->
    <div
      v-if="block.project"
      class="absolute left-0 top-0 bottom-0 w-1 shrink-0"
      :style="{ backgroundColor: block.project.color }"
    />

    <!-- Inhoud -->
    <div class="absolute inset-0 flex flex-col justify-between p-0.5 pl-1.5 overflow-hidden">
      <span
        v-if="isLargeEnough"
        class="text-[10px] leading-tight font-medium truncate"
        :class="block.project ? 'text-gray-800' : 'text-gray-500'"
      >
        {{ block.dominant_title }}
      </span>
      <span class="text-[9px] leading-none text-gray-400 self-end">
        {{ formatDuration(block.total_seconds) }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { parseLocalDate } from '@/utils/date'

const props = defineProps({
  block: { type: Object, required: true },
  isSelected: { type: Boolean, default: false },
  hourHeight: { type: Number, required: true },
})

const emit = defineEmits(['toggle'])

const MINUTES_PER_PX = 60 // hourHeight pixels = 60 minutes

const style = computed(() => {
  const start = parseLocalDate(props.block.started_at)
  const minutesFromMidnight = start.getHours() * 60 + start.getMinutes()
  const top = (minutesFromMidnight / 60) * props.hourHeight

  const durationMin = props.block.total_seconds / 60
  const height = Math.max((durationMin / 60) * props.hourHeight, 12)

  const bg = props.block.project
    ? props.block.project.color + '28'  // 16% opacity
    : '#f1f5f9'

  return {
    top: top + 'px',
    height: height + 'px',
    backgroundColor: bg,
  }
})

// Toon titel pas als blok hoog genoeg is
const isLargeEnough = computed(() => {
  const durationMin = props.block.total_seconds / 60
  return (durationMin / 60) * props.hourHeight >= 22
})

const formatDuration = (seconds) => {
  const m = Math.floor(seconds / 60)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  const rem = m % 60
  return rem > 0 ? `${h}u${rem}m` : `${h}u`
}
</script>
