import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/api'

export const useActivityRulesStore = defineStore('activityRules', () => {
  const rules     = ref([])
  const isLoading = ref(false)
  const error     = ref(null)

  async function fetchRules() {
    isLoading.value = true
    try {
      const res = await api.get('/activities/activity-rules/')
      const data = res.data
      rules.value = Array.isArray(data) ? data : (data.results ?? data)
    } catch (e) {
      error.value = e.response?.data?.detail ?? 'Fout bij ophalen regels'
    } finally {
      isLoading.value = false
    }
  }

  async function createRule(data) {
    try {
      const res = await api.post('/activities/activity-rules/', data)
      rules.value.push(res.data)
      return res.data
    } catch (e) {
      error.value = e.response?.data ?? 'Fout bij aanmaken regel'
      return null
    }
  }

  async function updateRule(id, data) {
    try {
      const res = await api.patch(`/activities/activity-rules/${id}/`, data)
      const idx = rules.value.findIndex(r => r.id === id)
      if (idx !== -1) rules.value[idx] = res.data
    } catch (e) {
      error.value = e.response?.data?.detail ?? 'Fout bij bijwerken regel'
    }
  }

  async function deleteRule(id) {
    try {
      await api.delete(`/activities/activity-rules/${id}/`)
      rules.value = rules.value.filter(r => r.id !== id)
    } catch (e) {
      error.value = e.response?.data?.detail ?? 'Fout bij verwijderen regel'
    }
  }

  async function applyRules(dateFrom, dateTo) {
    try {
      const res = await api.post('/activities/apply-rules/', { date_from: dateFrom, date_to: dateTo })
      return res.data
    } catch (e) {
      error.value = e.response?.data?.detail ?? 'Fout bij toepassen regels'
      return null
    }
  }

  function clearError() {
    error.value = null
  }

  return { rules, isLoading, error, fetchRules, createRule, updateRule, deleteRule, applyRules, clearError }
})
