// src/stores/activityBlocks.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/api'

// ── Mock data ──────────────────────────────────────────────────────────────────
function makeMockBlocks(mondayStr) {
  const monday = new Date(mondayStr)

  const makeBlock = (id, dayOffset, startHour, startMin, durationMin, title, project = null) => {
    const d = new Date(monday)
    d.setDate(d.getDate() + dayOffset)
    d.setHours(startHour, startMin, 0, 0)
    return {
      id,
      started_at: d.toISOString(),
      total_seconds: durationMin * 60,
      dominant_title: title,
      project,
    }
  }

  return [
    makeBlock(1,  0, 9,  0,  90, 'VS Code – TimeTracker', { id: 1, name: 'TimeTracker', color: '#6366f1' }),
    makeBlock(2,  0, 10, 30, 30, 'Chrome – GitHub'),
    makeBlock(3,  0, 11, 0,  60, 'Slack – #dev'),
    makeBlock(4,  0, 13, 0,  45, 'VS Code – TimeTracker', { id: 1, name: 'TimeTracker', color: '#6366f1' }),
    makeBlock(5,  0, 14, 0,  120,'VS Code – Django models'),
    makeBlock(6,  1, 9,  15, 75, 'Chrome – Docs'),
    makeBlock(7,  1, 11, 0,  30, 'Teams – standup'),
    makeBlock(8,  1, 14, 30, 90, 'VS Code – API views', { id: 2, name: 'Backend', color: '#f59e0b' }),
    makeBlock(9,  2, 8,  30, 60, 'Outlook – email'),
    makeBlock(10, 2, 10, 0,  45, 'VS Code – tests', { id: 2, name: 'Backend', color: '#f59e0b' }),
    makeBlock(11, 2, 13, 15, 105,'Chrome – Stack Overflow'),
    makeBlock(12, 3, 9,  0,  60, 'VS Code – frontend'),
    makeBlock(13, 3, 10, 30, 30, 'Figma – wireframes', { id: 3, name: 'Design', color: '#ec4899' }),
    makeBlock(14, 3, 14, 0,  60, 'VS Code – Vue components'),
    makeBlock(15, 4, 9,  30, 90, 'VS Code – bugfixes'),
    makeBlock(16, 4, 11, 30, 30, 'Chrome – localhost'),
    makeBlock(17, 4, 14, 0,  45, 'Teams – review'),
  ]
}

const MOCK_PROJECTS = [
  { id: 1, name: 'TimeTracker', color: '#6366f1' },
  { id: 2, name: 'Backend', color: '#f59e0b' },
  { id: 3, name: 'Design', color: '#ec4899' },
  { id: 4, name: 'Overig', color: '#64748b' },
]
// ──────────────────────────────────────────────────────────────────────────────

import { parseLocalDate, makeLocalISO, toLocalDateStr } from '@/utils/date'

function getMonday(dateStr) {
  const d = parseLocalDate(dateStr)
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + diff)
  return toLocalDateStr(d.toISOString())
}

// ── Helpers (ook gebruikt door resizeRange) ────────────────────────────────────
const blockStartMin = (block) => {
  const d = parseLocalDate(block.started_at)
  return d.getHours() * 60 + d.getMinutes()
}
const blockEndMin = (block) => blockStartMin(block) + block.total_seconds / 60

export const useActivityBlocksStore = defineStore('activityBlocks', () => {
  const today = toLocalDateStr(new Date().toISOString())

  const blocks         = ref([])
  const projects       = ref(MOCK_PROJECTS)
  const selectedBlocks = ref([])
  const currentDate    = ref(getMonday(today))
  const isLoading      = ref(false)
  const error          = ref(null)

  // ── Computed ───────────────────────────────────────────────────────────────
  const unassignedBlocks = computed(() =>
    blocks.value.filter(b => !b.project)
  )

  const mergedBlocksByDay = computed(() => {
    const map = {}
    for (const block of blocks.value) {
      const day = toLocalDateStr(block.started_at)
      if (!map[day]) map[day] = []
      map[day].push(block)
    }

    const result = {}
    for (const [day, dayBlocks] of Object.entries(map)) {
      const sorted = [...dayBlocks].sort((a, b) =>
        parseLocalDate(a.started_at) - parseLocalDate(b.started_at)
      )
      const merged = []
      let group = null
      for (const block of sorted) {
        const bStart    = blockStartMin(block)
        const bEnd      = blockEndMin(block)
        const projectId = block.project?.id ?? null
        if (group && projectId !== null && projectId === group.projectId && bStart <= group.endMin) {
          group.blocks.push(block)
          group.endMin = Math.max(group.endMin, bEnd)
        } else {
          if (group) merged.push(group)
          group = { blocks: [block], projectId, endMin: bEnd }
        }
      }
      if (group) merged.push(group)
      result[day] = merged
    }
    return result
  })

  // ── Actions ────────────────────────────────────────────────────────────────
  const toggleBlock = (blockId) => {
    const idx = selectedBlocks.value.indexOf(blockId)
    if (idx >= 0) selectedBlocks.value.splice(idx, 1)
    else selectedBlocks.value.push(blockId)
  }

  const toggleMany = (blockIds) => {
    const allSelected = blockIds.every(id => selectedBlocks.value.includes(id))
    if (allSelected) {
      selectedBlocks.value = selectedBlocks.value.filter(id => !blockIds.includes(id))
    } else {
      for (const id of blockIds) {
        if (!selectedBlocks.value.includes(id)) selectedBlocks.value.push(id)
      }
    }
  }

  const selectAll = () => {
    selectedBlocks.value = blocks.value.map(b => b.id)
  }

  const selectUnassigned = () => {
    selectedBlocks.value = unassignedBlocks.value.map(b => b.id)
  }

  const clearSelection = () => {
    selectedBlocks.value = []
  }

  const selectOrCreateRange = (iso, startMin, endMin) => {
    selectedBlocks.value = []
    const dayBlocks = blocks.value.filter(b => toLocalDateStr(b.started_at) === iso)

    for (let min = startMin; min < endMin; min += 15) {
      const slotStart = min
      const slotEnd   = min + 15

      const existing = dayBlocks.find(b => {
        const bStart = blockStartMin(b)
        const bEnd   = blockEndMin(b)
        return bStart < slotEnd && bEnd > slotStart
      })

      if (existing) {
        break
      } else {
        const d = parseLocalDate(iso)
        d.setHours(Math.floor(slotStart / 60), slotStart % 60, 0, 0)
        const newBlock = {
          id:            Date.now() + min,
          started_at:    d.toISOString(),
          total_seconds: 15 * 60,
          dominant_title: 'Nieuw blok',
          project:       null,
        }
        blocks.value.push(newBlock)
        selectedBlocks.value.push(newBlock.id)
      }
    }
  }

  // ── resizeRange (ontwerp B) ────────────────────────────────────────────────
  const resizeRange = async (iso, oldStartMin, oldEndMin, newStartMin, newEndMin, projectId) => {
    const project = projectId != null
      ? projects.value.find(p => p.id === projectId) ?? null
      : null

    const deletedBackendIds = []

    const groupBlocks = blocks.value.filter(b => {
      if (toLocalDateStr(b.started_at) !== iso) return false
      if ((b.project?.id ?? null) !== projectId)  return false
      const bStart = blockStartMin(b)
      const bEnd   = blockEndMin(b)
      return bStart < oldEndMin && bEnd > oldStartMin
    })

    for (const block of groupBlocks) {
      const bStart = blockStartMin(block)
      const bEnd   = blockEndMin(block)

      if (bEnd <= newStartMin || bStart >= newEndMin) {
        // Bewaar echte backend-IDs voor de delete-aanroep (temp-IDs zijn > 1e12)
        if (Number.isInteger(block.id) && block.id > 0 && block.id < 1e12) {
          deletedBackendIds.push(block.id)
        }
        const idx = blocks.value.findIndex(b => b.id === block.id)
        if (idx >= 0) blocks.value.splice(idx, 1)
        const selIdx = selectedBlocks.value.indexOf(block.id)
        if (selIdx >= 0) selectedBlocks.value.splice(selIdx, 1)
      } else {
        const clampedStart = Math.max(bStart, newStartMin)
        const clampedEnd   = Math.min(bEnd,   newEndMin)

        if (clampedStart !== bStart) {
          const d = parseLocalDate(iso)
          d.setHours(Math.floor(clampedStart / 60), clampedStart % 60, 0, 0)
          block.started_at = d.toISOString()
        }
        block.total_seconds = (clampedEnd - clampedStart) * 60
        block.project = project

        if (!selectedBlocks.value.includes(block.id)) {
          selectedBlocks.value.push(block.id)
        }
      }
    }

    // Nieuwe kwartierblokken voor lege slots binnen de nieuwe range
    const coveredMins = new Set()
    for (const b of blocks.value) {
      if (toLocalDateStr(b.started_at) !== iso) continue
      const bStart = blockStartMin(b)
      const bEnd   = blockEndMin(b)
      for (let m = bStart; m < bEnd; m += 15) coveredMins.add(m)
    }

    for (let m = newStartMin; m < newEndMin; m += 15) {
      if (!coveredMins.has(m)) {
        const d = parseLocalDate(iso)
        d.setHours(Math.floor(m / 60), m % 60, 0, 0)
        const newBlock = {
          id:             Date.now() * 1000 + m,
          started_at:     d.toISOString(),
          total_seconds:  15 * 60,
          dominant_title: project?.name ?? 'Nieuw blok',
          project,
        }
        blocks.value.push(newBlock)
        selectedBlocks.value.push(newBlock.id)
        coveredMins.add(m)
      }
    }

    // Verzamel alle blokken in het nieuwe bereik voor de bulk-sync
    const blocksToSync = blocks.value.filter(b => {
      if (toLocalDateStr(b.started_at) !== iso) return false
      const bStart = blockStartMin(b)
      const bEnd   = blockEndMin(b)
      return bStart < newEndMin && bEnd > newStartMin
    })

    // api.post wordt synchroon aangeroepen (vóór eerste await) zodat callers
    // zonder await toch de aanroep zien in tests en fire-and-forget werkt.
    const postPromise = api.post('/activities/activity-blocks/bulk/', {
      blocks: blocksToSync.map(b => ({
        id:            b.id,
        started_at:    b.started_at,
        total_seconds: b.total_seconds,
        project_id:    b.project?.id ?? null,
      })),
      deleted_ids: deletedBackendIds,
    })

    try {
      await postPromise
    } catch {
      await fetchWeekBlocks()
    }
  }

  // ── moveBlocks ─────────────────────────────────────────────────────────────
  const moveBlocks = async (blockIds, targetIso, deltaMin) => {
    // Bereken nieuwe started_at per blok en sla originals op voor rollback
    const patches = []
    for (const id of blockIds) {
      const block = blocks.value.find(b => b.id === id)
      if (!block) continue
      const oldMin  = blockStartMin(block)
      const newMin  = Math.max(0, Math.min(oldMin + deltaMin, 24 * 60 - 15))
      const snapped = Math.round(newMin / 15) * 15
      const d = parseLocalDate(targetIso)
      d.setHours(Math.floor(snapped / 60), snapped % 60, 0, 0)
      patches.push({ block, started_at: d.toISOString() })
    }

    // Optimistisch bijwerken
    for (const { block, started_at } of patches) {
      block.started_at = started_at
    }

    try {
      const results = await Promise.all(
        patches.map(({ block, started_at }) =>
          api.patch(`/activities/activity-blocks/${block.id}/`, { started_at })
        )
      )
      // Sla serverrespons op (bevat bijgewerkt ended_at en date)
      for (let i = 0; i < results.length; i++) {
        const idx = blocks.value.findIndex(b => b.id === patches[i].block.id)
        if (idx >= 0) blocks.value[idx] = results[i].data
      }
    } catch {
      await fetchWeekBlocks()
    }
  }

  const fetchWeekBlocks = async () => {
    isLoading.value = true
    error.value = null
    try {
      const endDate = parseLocalDate(currentDate.value)
      endDate.setDate(endDate.getDate() + 6)
      const endDateStr = toLocalDateStr(endDate.toISOString())
      const res = await api.get('/activities/activity-blocks/', {
        params: { date_from: currentDate.value, date_to: endDateStr },
      })
      blocks.value = res.data.results ?? res.data
      selectedBlocks.value = []
    } catch (err) {
      error.value = err.response?.data?.error ?? 'Fout bij ophalen blokken'
    } finally {
      isLoading.value = false
    }
  }

  const fetchProjects = async () => {
    try {
      const res = await api.get('/projects/')
      projects.value = res.data.results ?? res.data
    } catch {
      // Projecten zijn essentieel maar mislukken stil bij init
    }
  }

  const createBlock = async (slotInfo, projectId) => {
    const project = projectId ? projects.value.find(p => p.id === projectId) : null
    const tempId = Date.now()
    const newBlock = {
      id:             tempId,
      started_at:     makeLocalISO(slotInfo.iso, slotInfo.hour, slotInfo.minute),
      total_seconds:  15 * 60,
      dominant_title: project?.name ?? 'Nieuw blok',
      project:        project ?? null,
    }
    blocks.value.push(newBlock)

    try {
      const res = await api.post('/activities/activity-blocks/', {
        started_at:    newBlock.started_at,
        total_seconds: newBlock.total_seconds,
        project_id:    projectId ?? null,
      })
      const idx = blocks.value.findIndex(b => b.id === tempId)
      if (idx >= 0) blocks.value[idx] = res.data
    } catch {
      const idx = blocks.value.findIndex(b => b.id === tempId)
      if (idx >= 0) blocks.value.splice(idx, 1)
    }
  }

  const assignToProject = async (projectId) => {
    const project = projects.value.find(p => p.id === projectId)
    if (!project) return

    const blockIds = [...selectedBlocks.value]

    // Optimistisch bijwerken
    for (const id of blockIds) {
      const block = blocks.value.find(b => b.id === id)
      if (block) block.project = project
    }
    selectedBlocks.value = []

    try {
      await api.post('/activities/activity-blocks/assign/', {
        block_ids: blockIds,
        project_id: projectId,
      })
    } catch {
      await fetchWeekBlocks() // terug naar server-staat (rollback optimistische update)
      error.value = 'Fout bij toewijzen project'
    }
  }

  const applyRules = async () => {
    isLoading.value = true
    error.value = null
    try {
      const endDate = parseLocalDate(currentDate.value)
      endDate.setDate(endDate.getDate() + 6)
      const endDateStr = toLocalDateStr(endDate.toISOString())
      await api.post('/activities/apply-rules/', {
        date_from: currentDate.value,
        date_to:   endDateStr,
      })
      await fetchWeekBlocks()
    } catch {
      error.value = 'Fout bij auto-toewijzen'
    } finally {
      isLoading.value = false
    }
  }

  const goToPrevWeek = () => {
    const d = parseLocalDate(currentDate.value)
    d.setDate(d.getDate() - 7)
    currentDate.value = toLocalDateStr(d.toISOString())
    fetchWeekBlocks()
  }

  const goToNextWeek = () => {
    const d = parseLocalDate(currentDate.value)
    d.setDate(d.getDate() + 7)
    currentDate.value = toLocalDateStr(d.toISOString())
    fetchWeekBlocks()
  }

  return {
    blocks, projects, selectedBlocks, currentDate,
    isLoading, error, unassignedBlocks, mergedBlocksByDay,
    toggleBlock, toggleMany,
    selectAll, selectUnassigned, clearSelection, selectOrCreateRange,
    fetchWeekBlocks, fetchProjects, createBlock, assignToProject, applyRules,
    goToPrevWeek, goToNextWeek,
    resizeRange, moveBlocks,
  }
})
