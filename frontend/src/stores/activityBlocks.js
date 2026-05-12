// src/stores/activityBlocks.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
// import api from '@/api/api'  // Uncomment als backend klaar is

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
  return d.toISOString().split('T')[0]
}

// Helper om een lokale datum+tijd te maken zonder tijdzone verschuiving
export const useActivityBlocksStore = defineStore('activityBlocks', () => {
  const today = new Date().toISOString().split('T')[0]

  const blocks = ref([])
  const projects = ref(MOCK_PROJECTS)
  const selectedBlocks = ref([])
  const currentDate = ref(getMonday(today))
  const isLoading = ref(false)
  const error = ref(null)

  // ── Computed ───────────────────────────────────────────────────────────────
  const unassignedBlocks = computed(() =>
    blocks.value.filter(b => !b.project)
  )

const blocksByDay = computed(() => {
  const map = {}
  for (const block of blocks.value) {
    const d = parseLocalDate(block.started_at)
    // Gebruik lokale datum, niet UTC
    const day = toLocalDateStr(block.started_at)
    if (!map[day]) map[day] = []
    map[day].push(block)
  }
  return map
})

const mergedBlocksByDay = computed(() => {
  const result = {}
  for (const [day, dayBlocks] of Object.entries(blocksByDay.value)) {
    const sorted = [...dayBlocks].sort((a, b) =>
      parseLocalDate(a.started_at) - parseLocalDate(b.started_at)
    )
    const merged = []
    let group = null
    for (const block of sorted) {
      const bDate = parseLocalDate(block.started_at)
      const bStart = bDate.getHours() * 60 + bDate.getMinutes()
      const bEnd = bStart + Math.round(block.total_seconds / 60)
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

  // Selecteer bestaande blokken in een tijdrange, maak nieuwe aan voor lege slots
    const selectOrCreateRange = (iso, startMin, endMin) => {
        selectedBlocks.value = []
        const dayBlocks = blocks.value.filter(b => toLocalDateStr(b.started_at) === iso)

        for (let min = startMin; min < endMin; min += 15) {
            const slotStart = min
            const slotEnd = min + 15

            const existing = dayBlocks.find(b => {
                const bDate = parseLocalDate(b.started_at)
                const bStart = bDate.getHours() * 60 + bDate.getMinutes()
                const bEnd = bStart + Math.round(b.total_seconds / 60)
                return bStart < slotEnd && bEnd > slotStart
            })

            if (existing) {
                break
            } else {
                const d = parseLocalDate(iso)
                d.setHours(Math.floor(slotStart / 60), slotStart % 60, 0, 0)
                const newBlock = {
                    id: Date.now() + min,
                    started_at: d.toISOString(),
                    total_seconds: 15 * 60,
                    dominant_title: 'Nieuw blok',
                    project: null,
                }
                blocks.value.push(newBlock)
                selectedBlocks.value.push(newBlock.id)
            }
        }
    }

  const fetchWeekBlocks = async () => {
    isLoading.value = true
    error.value = null
    try {
      // ── Gebruik mock data ──────────────────────────────────────────────────
      await new Promise(r => setTimeout(r, 300)) // Simuleer netwerk
      blocks.value = makeMockBlocks(currentDate.value)
      selectedBlocks.value = []

      // ── Backend (uncomment als klaar) ──────────────────────────────────────
      // const endDate = new Date(currentDate.value)
      // endDate.setDate(endDate.getDate() + 6)
      // const res = await api.get('/activity-blocks/', {
      //   params: { start_date: currentDate.value, end_date: endDate.toISOString().split('T')[0] }
      // })
      // blocks.value = res.data.results ?? res.data
      // selectedBlocks.value = []
    } catch (err) {
      error.value = err.response?.data?.error ?? 'Fout bij ophalen blokken'
    } finally {
      isLoading.value = false
    }
  }

  const createBlock = (slotInfo, projectId) => {
    const project = projectId ? projects.value.find(p => p.id === projectId) : null
    const newBlock = {
      id: Date.now(), // tijdelijk ID, backend geeft echte
      started_at: makeLocalISO(slotInfo.iso, slotInfo.hour, slotInfo.minute),
      total_seconds: 15 * 60, // standaard 15 minuten
      dominant_title: project?.name ?? 'Nieuw blok',
      project: project ?? null,
    }
    blocks.value.push(newBlock)

    // ── Backend (uncomment als klaar) ──────────────────────────────────────
    // api.post('/activity-blocks/', {
    //   started_at: newBlock.started_at,
    //   total_seconds: newBlock.total_seconds,
    //   project: projectId,
    // })
  }

  const assignToProject = async (projectId) => {
    const project = projects.value.find(p => p.id === projectId)
    if (!project) return

    // Optimistisch updaten
    for (const id of selectedBlocks.value) {
      const block = blocks.value.find(b => b.id === id)
      if (block) block.project = project
    }
    selectedBlocks.value = []

    // ── Backend (uncomment als klaar) ──────────────────────────────────────
    // try {
    //   await api.post('/activity-blocks/assign/', {
    //     block_ids: selectedBlocks.value,
    //     project_id: projectId,
    //   })
    // } catch (err) {
    //   error.value = 'Fout bij toewijzen project'
    //   await fetchWeekBlocks() // Herlaad bij fout
    // }
  }

  const applyRules = async () => {
    isLoading.value = true
    try {
      // ── Backend (uncomment als klaar) ──────────────────────────────────────
      // await api.post('/activity-blocks/apply-rules/')
      // await fetchWeekBlocks()

      // Mock: wijs eerste project toe aan ongekoppelde blokken die VS Code bevatten
      for (const block of unassignedBlocks.value) {
        if (block.dominant_title?.includes('VS Code')) {
          block.project = projects.value[0]
        }
      }
    } catch (err) {
      error.value = 'Fout bij auto-toewijzen'
    } finally {
      isLoading.value = false
    }
  }

  const goToPrevWeek = () => {
    const d = parseLocalDate(currentDate.value)
    d.setDate(d.getDate() - 7)
    currentDate.value = d.toISOString().split('T')[0]
    fetchWeekBlocks()
  }

  const goToNextWeek = () => {
    const d = parseLocalDate(currentDate.value)
    d.setDate(d.getDate() + 7)
    currentDate.value = d.toISOString().split('T')[0]
    fetchWeekBlocks()
  }

  return {
    blocks, projects, selectedBlocks, currentDate,
    isLoading, error, unassignedBlocks, blocksByDay, mergedBlocksByDay,
    toggleBlock, selectAll, selectUnassigned, clearSelection, selectOrCreateRange,
    fetchWeekBlocks, createBlock, assignToProject, applyRules,
    goToPrevWeek, goToNextWeek,
  }
})
