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
        <div class="text-[10px] text-gray-400 mt-0.5 h-3">
          {{ day.showMonth ? day.month : '' }}
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
          :data-iso="day.iso"
          class="relative border-r border-gray-200 last:border-r-0 select-none"
          :style="{ height: totalHeight + 'px' }"
          :class="[
            day.isToday ? 'bg-blue-50/20' : '',
            activeResize ? 'cursor-ns-resize' : (activeMove ? 'cursor-grabbing' : 'cursor-crosshair'),
          ]"
          @mousedown="onColumnMouseDown($event, day.iso)"
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

          <!-- Selectie-drag overlay -->
          <div
            v-if="selDrag && selDrag.iso === day.iso"
            class="absolute inset-x-0.5 bg-blue-400/20 border border-blue-400 rounded pointer-events-none z-10"
            :style="selDragStyle"
          />

          <!-- Move-preview ghost -->
          <div
            v-if="activeMove && activeMove.previewIso === day.iso"
            class="absolute left-1 right-1 rounded border-2 border-dashed border-blue-400 bg-blue-50/60 pointer-events-none z-25"
            :style="movePreviewStyle"
          />

          <!-- Resize-preview ghost -->
          <div
            v-if="activeResize && activeResize.iso === day.iso"
            class="absolute left-1 right-1 rounded border-2 border-dashed border-violet-400 bg-violet-50/60 pointer-events-none z-25"
            :style="resizePreviewStyle"
          />

          <!-- Blokken -->
          <ActivityBlock
            v-for="group in mergedBlocksByDay[day.iso] ?? []"
            :key="group.blocks[0].id"
            :blocks="group.blocks"
            :is-selected="group.blocks.every(b => selectedBlocks.includes(b.id))"
            :is-dragging="!!activeMove && activeMove.blockIds.some(id => group.blocks.find(b => b.id === id))"
            :hour-height="hourHeight"
            @move-start="onMoveStart($event, day.iso)"
            @resize-start="onResizeStart($event, day.iso)"
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
import { parseLocalDate, toLocalDateStr } from '@/utils/date'
import ActivityBlock from '@/components/ActivityBlock.vue'
import SlotSuggestion from '@/components/SlotSuggestion.vue'

const store   = useActivityBlocksStore()
const gridEl  = ref(null)

const hourHeight  = 56
const totalHeight = 24 * hourHeight

const gridCols = computed(() => ({ gridTemplateColumns: `48px repeat(7, minmax(0, 1fr))` }))

const selectedBlocks    = computed(() => store.selectedBlocks)
const mergedBlocksByDay = computed(() => store.mergedBlocksByDay)

// ── Weekdagen ──────────────────────────────────────────────────────────────────
const daysOfWeek = computed(() => {
  const todayStr = toLocalDateStr(new Date().toISOString())
  const monday   = new Date(store.currentDate)
  return Array.from({ length: 7 }, (_, i) => {
    const d   = new Date(monday)
    d.setDate(monday.getDate() + i)
    const iso = toLocalDateStr(d.toISOString())
    return {
      iso,
      isToday:  iso === todayStr,
      weekday:  d.toLocaleDateString('nl-NL', { weekday: 'short' }),
      dayNum:   d.getDate(),
      showMonth: i === 0 || d.getDate() === 1,
      month:    d.toLocaleDateString('nl-NL', { month: 'short' }),
    }
  })
})

// ── Huidige tijd ───────────────────────────────────────────────────────────────
const currentTimeTop = ref(null)
let timer = null
const updateCurrentTime = () => {
  const now = new Date()
  currentTimeTop.value = (now.getHours() * 60 + now.getMinutes()) / 60 * hourHeight
}
onMounted(() => { updateCurrentTime(); timer = setInterval(updateCurrentTime, 60_000) })
onUnmounted(() => clearInterval(timer))

// ── Pure helpers (geen store-referenties) ──────────────────────────────────────
const snap   = (min) => Math.round(min / 15) * 15
const clamp  = (min) => Math.max(0, Math.min(min, 24 * 60 - 15))
const yToMin = (y)   => snap(Math.floor(y / hourHeight * 60))

/** Viewport-rect van een dagkolom */
const colRect = (iso) => {
  const el = gridEl.value?.querySelector(`[data-iso="${iso}"]`)
  return el ? el.getBoundingClientRect() : null
}

/** ISO van de kolom onder clientX */
const isoAtX = (clientX) => {
  const cols = gridEl.value?.querySelectorAll('[data-iso]') ?? []
  for (const col of cols) {
    const r = col.getBoundingClientRect()
    if (clientX >= r.left && clientX < r.right) return col.dataset.iso
  }
  return null
}

/** Startminuut van een blok binnen de dag */
const blockStartMin = (block) => {
  const d = parseLocalDate(block.started_at)
  return d.getHours() * 60 + d.getMinutes()
}
const blockEndMin = (block) => blockStartMin(block) + block.total_seconds / 60


// ════════════════════════════════════════════════════════════════════════════════
// 1. SELECTIE-DRAG  (slepen op leeg grid)
// ════════════════════════════════════════════════════════════════════════════════
const selDrag = ref(null) // { iso, startMin, curMin, rect }

const selDragStyle = computed(() => {
  if (!selDrag.value) return {}
  const start  = Math.min(selDrag.value.startMin, selDrag.value.curMin)
  const end    = Math.max(selDrag.value.startMin, selDrag.value.curMin) + 15
  const top    = (start / 60) * hourHeight
  const height = ((end - start) / 60) * hourHeight
  return { top: top + 'px', height: Math.max(height, 4) + 'px' }
})

const onSelDragMove = (e) => {
  if (!selDrag.value) return
  const y = Math.max(0, Math.min(e.clientY - selDrag.value.rect.top, totalHeight))
  selDrag.value = { ...selDrag.value, curMin: yToMin(y) }
}

const onSelDragUp = (e) => {
  window.removeEventListener('mousemove', onSelDragMove)
  window.removeEventListener('mouseup',   onSelDragUp)
  if (!selDrag.value) return

  const { iso, startMin, curMin } = selDrag.value
  selDrag.value = null

  const rangeStart = Math.min(startMin, curMin)
  const rangeEnd   = Math.max(startMin, curMin) + 15
  const wasDrag    = rangeEnd - rangeStart > 15

  const containerRect = gridEl.value.getBoundingClientRect()
  const popupTop  = e.clientY - containerRect.top + gridEl.value.scrollTop + 8
  const popupLeft = Math.min(e.clientX - containerRect.left + 8, containerRect.width - 240)

  if (wasDrag) {
    store.selectOrCreateRange(iso, rangeStart, rangeEnd)
    suggestion.value = {
      slotInfo: { iso, hour: Math.floor(rangeStart / 60), minute: rangeStart % 60 },
      position: { top: popupTop + 'px', left: popupLeft + 'px' },
      isRange:  true,
    }
  } else {
    suggestion.value = {
      slotInfo: { iso, hour: Math.floor(rangeStart / 60), minute: rangeStart % 60 },
      position: { top: popupTop + 'px', left: popupLeft + 'px' },
      isRange:  false,
    }
  }
}


// ════════════════════════════════════════════════════════════════════════════════
// 2. MOVE-DRAG  (blok verslepen)
// Slaat alleen primitieven op — geen block-object referenties.
// ════════════════════════════════════════════════════════════════════════════════
/**
 * activeMove: {
 *   blockIds:       number[]  — IDs van de groep
 *   origIso:        string    — dag bij mousedown
 *   origStartMin:   number    — startminuut van eerste blok bij mousedown
 *   durationMin:    number    — visuele duur van de groep
 *   clickOffsetMin: number    — klikpositie t.o.v. blok-top
 *   projectId:      number|null
 *   previewIso:     string    — dag van de live preview
 *   previewStart:   number    — startminuut van de live preview
 *   moved:          boolean
 * }
 */
const activeMove = ref(null)

const movePreviewStyle = computed(() => {
  if (!activeMove.value) return {}
  const { previewStart, durationMin } = activeMove.value
  return {
    top:    (previewStart / 60) * hourHeight + 'px',
    height: Math.max((durationMin / 60) * hourHeight, 12) + 'px',
  }
})

const onMoveStart = ({ event, blocks }, iso) => {
  if (event.button !== 0) return

  const first      = blocks[0]
  const last       = blocks[blocks.length - 1]
  const origStart  = blockStartMin(first)
  const duration   = blockEndMin(last) - origStart
  const projectId  = first.project?.id ?? null

  const rect     = colRect(iso)
  if (!rect) return
  const clickMin = yToMin(Math.max(0, event.clientY - rect.top))

  activeMove.value = {
    blockIds:       blocks.map(b => b.id),
    origIso:        iso,
    origStartMin:   origStart,
    durationMin:    duration,
    clickOffsetMin: clickMin - origStart,
    projectId,
    previewIso:     iso,
    previewStart:   origStart,
    moved:          false,
  }

  window.addEventListener('mousemove', onMoveDragMove)
  window.addEventListener('mouseup',   onMoveDragUp)
}

const onMoveDragMove = (e) => {
  if (!activeMove.value) return
  const targetIso = isoAtX(e.clientX) ?? activeMove.value.previewIso
  const rect      = colRect(targetIso)
  if (!rect) return

  const y         = e.clientY - rect.top
  const clickMin  = yToMin(Math.max(0, Math.min(y, totalHeight)))
  const newStart  = clamp(snap(clickMin - activeMove.value.clickOffsetMin))
  const moved     = activeMove.value.moved ||
    newStart !== activeMove.value.previewStart ||
    targetIso !== activeMove.value.previewIso

  activeMove.value = { ...activeMove.value, previewIso: targetIso, previewStart: newStart, moved }
}

const onMoveDragUp = () => {
  window.removeEventListener('mousemove', onMoveDragMove)
  window.removeEventListener('mouseup',   onMoveDragUp)
  if (!activeMove.value) return

  const move = activeMove.value
  activeMove.value = null

  if (!move.moved) {
    // Geen beweging → toggle selectie
    store.toggleMany(move.blockIds)
    return
  }

  const deltaMin = move.previewStart - move.origStartMin
  store.moveBlocks(move.blockIds, move.previewIso, deltaMin)
}


// ════════════════════════════════════════════════════════════════════════════════
// 3. RESIZE-DRAG  (rand slepen)
// Slaat alleen primitieven op — de store zoekt zelf de blokken op bij mouseup.
// ════════════════════════════════════════════════════════════════════════════════
/**
 * activeResize: {
 *   iso:          string       — dag
 *   projectId:    number|null  — project van de groep (om de juiste blokken te vinden)
 *   oldStartMin:  number       — startminuut van de groep bij mousedown
 *   oldEndMin:    number       — eindminuut van de groep bij mousedown
 *   fixedMin:     number       — het vaste uiteinde (beweegt NIET mee)
 *   curMin:       number       — het uiteinde dat de gebruiker sleept
 *   edge:         'top'|'bottom'
 * }
 */
const activeResize = ref(null)

const resizePreviewStyle = computed(() => {
  if (!activeResize.value) return {}
  const { fixedMin, curMin, edge } = activeResize.value
  // bottom-resize: vast = top,    sleep = bodem
  // top-resize:    vast = bodem,  sleep = top
  const startMin = edge === 'bottom' ? fixedMin                    : curMin
  const endMin   = edge === 'bottom' ? curMin                      : fixedMin
  return {
    top:    (startMin / 60) * hourHeight + 'px',
    height: Math.max(((endMin - startMin) / 60) * hourHeight, 12) + 'px',
  }
})

const onResizeStart = ({ event, blocks, edge }, iso) => {
  if (event.button !== 0) return

  const first      = blocks[0]
  const last       = blocks[blocks.length - 1]
  const oldStartMin = blockStartMin(first)
  const oldEndMin   = blockEndMin(last)
  const projectId   = first.project?.id ?? null

  // fixedMin = het uiteinde dat NIET beweegt
  // curMin   = het uiteinde dat de gebruiker sleept (begint op de huidige rand)
  const fixedMin = edge === 'bottom' ? oldStartMin : oldEndMin
  const curMin   = edge === 'bottom' ? oldEndMin   : oldStartMin

  activeResize.value = {
    iso,
    projectId,
    oldStartMin,
    oldEndMin,
    fixedMin,
    curMin,
    edge,
  }

  window.addEventListener('mousemove', onResizeDragMove)
  window.addEventListener('mouseup',   onResizeDragUp)
}

const onResizeDragMove = (e) => {
  if (!activeResize.value) return
  const rect = colRect(activeResize.value.iso)
  if (!rect) return

  const y      = e.clientY - rect.top
  const rawMin = snap(Math.max(0, Math.min(y / hourHeight * 60, 24 * 60)))

  // Blokkeer omkeren: bodem mag niet boven top, top mag niet onder bodem
  const { edge, fixedMin } = activeResize.value
  const newCurMin = edge === 'bottom'
    ? Math.max(rawMin, fixedMin + 15)  // bodem ≥ top + 15
    : Math.min(rawMin, fixedMin - 15)  // top ≤ bodem - 15

  activeResize.value = { ...activeResize.value, curMin: newCurMin }
}

const onResizeDragUp = () => {
  window.removeEventListener('mousemove', onResizeDragMove)
  window.removeEventListener('mouseup',   onResizeDragUp)
  if (!activeResize.value) return

  const { iso, projectId, oldStartMin, oldEndMin, fixedMin, curMin, edge } = activeResize.value
  activeResize.value = null

  // Nieuwe range — zelfde formule als resizePreviewStyle
  const newStartMin = edge === 'bottom' ? fixedMin : curMin
  const newEndMin   = edge === 'bottom' ? curMin   : fixedMin

  // Geef alleen primitieven door aan de store
  store.resizeRange(iso, oldStartMin, oldEndMin, newStartMin, newEndMin, projectId)
}


// ════════════════════════════════════════════════════════════════════════════════
// Kolom mousedown — alleen op lege achtergrond
// ════════════════════════════════════════════════════════════════════════════════
const onColumnMouseDown = (event, iso) => {
  if (event.button !== 0) return
  if (event.target.closest('.activity-block')) return

  suggestion.value = null
  const rect    = event.currentTarget.getBoundingClientRect()
  const minutes = yToMin(event.clientY - rect.top)

  selDrag.value = { iso, startMin: minutes, curMin: minutes, rect }
  window.addEventListener('mousemove', onSelDragMove)
  window.addEventListener('mouseup',   onSelDragUp)
}


// ── Popup ──────────────────────────────────────────────────────────────────────
const suggestion = ref(null)

const onCreateBlock = ({ projectId, slotInfo }) => {
  if (suggestion.value?.isRange) {
    store.assignToProject(projectId)
  } else {
    store.createBlock(slotInfo, projectId)
  }
  suggestion.value = null
}

const onOutsideClick = (e) => {
  if (suggestion.value && !e.target.closest('.slot-suggestion')) {
    suggestion.value = null
  }
}
onMounted(() => document.addEventListener('mousedown', onOutsideClick))
onUnmounted(() => document.removeEventListener('mousedown', onOutsideClick))
</script>
