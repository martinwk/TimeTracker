import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/api'

export const useProjectsStore = defineStore('projects', () => {
  const projects  = ref([])
  const isLoading = ref(false)
  const error     = ref(null)

  async function fetchProjects() {
    isLoading.value = true
    try {
      const res = await api.get('/projects/')
      const data = res.data
      projects.value = Array.isArray(data) ? data : (data.results ?? data)
    } catch (e) {
      error.value = e.response?.data?.detail ?? 'Fout bij ophalen projecten'
    } finally {
      isLoading.value = false
    }
  }

  async function createProject(data) {
    try {
      const res = await api.post('/projects/', data)
      projects.value.push(res.data)
      return res.data
    } catch (e) {
      error.value = e.response?.data ?? 'Fout bij aanmaken project'
      return null
    }
  }

  async function updateProject(id, data) {
    try {
      const res = await api.patch(`/projects/${id}/`, data)
      const idx = projects.value.findIndex(p => p.id === id)
      if (idx !== -1) projects.value[idx] = res.data
    } catch (e) {
      error.value = e.response?.data?.detail ?? 'Fout bij bijwerken project'
    }
  }

  async function deleteProject(id) {
    try {
      await api.delete(`/projects/${id}/`)
      projects.value = projects.value.filter(p => p.id !== id)
    } catch (e) {
      error.value = e.response?.data?.detail ?? 'Fout bij verwijderen project'
    }
  }

  function clearError() {
    error.value = null
  }

  return { projects, isLoading, error, fetchProjects, createProject, updateProject, deleteProject, clearError }
})
