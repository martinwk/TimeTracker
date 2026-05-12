<template>
  <div class="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">

    <!-- Dag-headers -->
    <div class="grid border-b border-gray-200 bg-gray-50 sticky top-0 z-30" :style="gridCols">
      <div class="py-2 border-r border-gray-200" />
      <div
        v-for="day in daysOfWeek"
        :key="day.iso"
        class="py-2 px-1 text-center border-r border-gray-200 last:border-r-0"
        :class="day.isToday ? 'bg-blue-50' : ''"
      >
        <div class="text-[11px] uppercase tracking-wide font-semibold text-gray-400">{{ day.weekday }}</div>
        <div
          class="text-sm font-bold mt-0.5 w-7 h-7 mx-auto flex items-center justify-center rounded-full"
          :class="day.isToday ? 'bg-blue-500 text-white' : 'text-gray-700'"
        >
          {{ day.dayNum }}
        </div>
      </div>
    </div>

    <!-- Grid lichaam -->
    <div class="overflow-y-auto relative" style="max-height: 72vh;" ref="gridEl">
      <div class="grid" :style="gridCols">

        <!-- Tijdlabel kolom -->
        <div class="relative border-r border-gray-200" :style="{ height: totalHeight + 'px', minWidth: '48px' }">
          <div
            v-for="h in 24"
            :key="h"
            class="absolute right-1 text-[10px] text-gray-300 font-mono leading-none"
            :style="{ top: (h - 1) * hourHeight - 6 + 'px' }"
          >
            {{ String(h - 1).padStart(2, '0') }}:00
          </div>
        </div>

        <!-- Dag-kolommen -->
        <div
          v-for="day in daysOfWeek"
          :key="day.iso"
          class="relative border-r border-gray-200 last:border-r-0 cursor-crosshair select-none"
          :style="{ height: totalHeight + 'px' }"
          :class="day.isToday ? 'bg-blue-50/20' : ''"
          @mousedown="onMouseDown($event, day)"
        >
          <!-- Uurlijnen -->
          <div
            v-for="h in 24"
            :key="h"
            class="absolute inset-x-0 border-t pointer-events-none"
            :class="(h - 1) % 2 === 0 ? 'border-gray-100' : 'border-gray-50'"
            :style="{ top: (h - 1) * hourHeight + 'px' }"
          />

          <!-- Huidige-tijd lijn -->
          <div
            v-if="day.isToday && currentTimeTop !== null"
            class="absolute inset-x-0 z-20 pointer-events-none flex items-center"
            :style="{ top: currentTimeTop + 'px' }"
          >
            <div class="w-2 h-2 rounded-full bg-red-400 shrink-0 -ml-1" />
            <div class="flex-1 border-t border-red-400" />
          </div>

          <!-- Drag selectie overlay -->
          <div
            v-if="drag && drag.iso === day.iso"
            class="absolute inset-x-0.5 bg-blue-400/20 border border-blue-400 rounded pointer-events-none z-10"
            :style="dragOverlayStyle"
          />

          <!-- Blokken -->
          <ActivityBlock
            v-for="block in blocksByDay[day.iso] ?? []"
            :key="block.id"
            :block="block"
            :is-selected="selectedBlocks.includes(block.id)"
            :hour-height="hourHeight"
            @toggle="store.toggleBlock"
          />
        </div>

      </div>

      <!-- Slot suggestie popup -->
      <SlotSuggestion
        v-if="suggestion"
        :slot-info="suggestion.slotInfo"
        :position="suggestion.position"
        @create="onCreateBlock"
        @close="suggestion = null"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useActivityBlocksStore } from '@/stores/activityBlocks'
import ActivityBlock from '@/components/ActivityBlock.vue'
import SlotSuggestion from '@/components/SlotSuggestion.vue'

const store = useActivityBlocksStore()
const gridEl = ref(null)

const hourHeight = 56
const totalHeight = 24 * hourHeight

const gridCols = computed(() => ({
  gridTemplateColumns: `48px repeat(7, minmax(0, 1fr))`
}))

const selectedBlocks = computed(() => store.selectedBlocks)
const blocksByDay = computed(() => store.blocksByDay)

const daysOfWeek = computed(() => {
  const todayStr = new Date().toISOString().split('T')[0]
  const monday = new Date(store.currentDate)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    const iso = d.toISOString().split('T')[0]
    return {
      iso,
      isToday: iso === todayStr,
      weekday: d.toLocaleDateString('nl-NL', { weekday: 'short' }),
      dayNum: d.getDate(),
    }
  })
})

// Huidige tijd
const currentTimeTop = ref(null)
let timer = null
const updateCurrentTime = () => {
  const now = new Date()
  currentTimeTop.value = (now.getHours() * 60 + now.getMinutes()) / 60 * hourHeight
}
onMounted(() => { updateCurrentTime(); timer = setInterval(updateCurrentTime, 60_000) })
onUnmounted(() => clearInterval(timer))

// ── Drag selectie ────────────────────────────────────────────────────────────
const drag = ref(null) // { iso, startMinutes, currentMinutes, startY, rect }

const yToMinutes = (y) => {
  const minutes = Math.floor(y / hourHeight * 60)
  return Math.floor(minutes / 15) * 15 // snap naar kwartier
}

const dragOverlayStyle = computed(() => {
  if (!drag.value) return {}
  const start = Math.min(drag.value.startMinutes, drag.value.currentMinutes)
  const end = Math.max(drag.value.startMinutes, drag.value.currentMinutes) + 15
  const top = (start / 60) * hourHeight
  const height = ((end - start) / 60) * hourHeight
  return { top: top + 'px', height: Math.max(height, 4) + 'px' }
})

const onMouseDown = (event, day) => {
  // Alleen linkermuisknop
  if (event.button !== 0) return
  suggestion.value = null

  const rect = event.currentTarget.getBoundingClientRect()
  const y = event.clientY - rect.top
  const minutes = yToMinutes(y)

  drag.value = {
    iso: day.iso,
    startMinutes: minutes,
    currentMinutes: minutes,
    rect,
  }

  // Voeg globale listeners toe
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

const onMouseMove = (event) => {
  if (!drag.value) return
  const y = event.clientY - drag.value.rect.top
  const clampedY = Math.max(0, Math.min(y, totalHeight))
  drag.value.currentMinutes = yToMinutes(clampedY)
}

const onMouseUp = (event) => {
  if (!drag.value) return

  const startMin = Math.min(drag.value.startMinutes, drag.value.currentMinutes)
  const endMin = Math.max(drag.value.startMinutes, drag.value.currentMinutes) + 15
  const iso = drag.value.iso
  const wasDrag = endMin - startMin > 15 // meer dan één kwartier = echte drag

  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)

  if (wasDrag) {
    // Selecteer/maak blokken in de range aan
    store.selectOrCreateRange(iso, startMin, endMin)

    // Toon popup om project toe te wijzen
    const containerRect = gridEl.value.getBoundingClientRect()
    const popupTop = event.clientY - containerRect.top + gridEl.value.scrollTop + 8
    const popupLeft = event.clientX - containerRect.left + 8
    const left = Math.min(popupLeft, containerRect.width - 240)

    suggestion.value = {
      slotInfo: { iso, hour: Math.floor(startMin / 60), minute: startMin % 60 },
      position: { top: popupTop + 'px', left: left + 'px' },
      isRange: true,
    }
  } else {
    // Gewone klik — maak één blok aan
    const hour = Math.floor(startMin / 60)
    const minute = startMin % 60
    const containerRect = gridEl.value.getBoundingClientRect()
    const popupTop = event.clientY - containerRect.top + gridEl.value.scrollTop + 8
    const popupLeft = event.clientX - containerRect.left + 8
    const left = Math.min(popupLeft, containerRect.width - 240)

    suggestion.value = {
      slotInfo: { iso, hour, minute },
      position: { top: popupTop + 'px', left: left + 'px' },
      isRange: false,
    }
  }

  drag.value = null
}

// ── Popup ────────────────────────────────────────────────────────────────────
const suggestion = ref(null)

const onCreateBlock = ({ projectId, slotInfo }) => {
  if (suggestion.value?.isRange) {
    // Range: wijs project toe aan alle geselecteerde blokken
    store.assignToProject(projectId)
  } else {
    // Enkel blok aanmaken
    store.createBlock(slotInfo, projectId)
  }
  suggestion.value = null
}

// Sluit popup bij klik buiten
const onOutsideClick = (event) => {
  if (suggestion.value && !event.target.closest('.slot-suggestion')) {
    suggestion.value = null
  }
}
onMounted(() => document.addEventListener('mousedown', onOutsideClick))
onUnmounted(() => document.removeEventListener('mousedown', onOutsideClick))
</script>
