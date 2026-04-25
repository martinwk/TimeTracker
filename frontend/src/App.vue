<template>
  <div class="flex">
    <Sidebar />

    <main class="flex-1 bg-gray-100 p-8">
      <h1 class="text-4xl font-bold text-blue-600">
        🎉 TimeTracker Vue App
      </h1>

      <!-- Projects Section -->
      <div class="mt-8 bg-white p-6 rounded-lg shadow">
        <h2 class="text-2xl font-bold mb-4">Projects from Django</h2>

        <!-- Loading indicator -->
        <div v-if="loading" class="text-gray-600">
          Loading projects...
        </div>

        <!-- Error message -->
        <div v-if="error" class="text-red-600">
          Error: {{ error }}
        </div>

        <!-- Projects list -->
        <div v-if="!loading && projects.length > 0" class="space-y-3">
          <div
            v-for="project in projects"
            :key="project.id"
            class="p-4 border border-gray-300 rounded"
          >
            <h3 class="font-bold text-lg">{{ project.name }}</h3>
            <p class="text-sm text-gray-600">Color: {{ project.color }}</p>
            <p class="text-sm text-gray-600">Active: {{ project.is_active }}</p>
          </div>
        </div>

        <!-- No projects -->
        <div v-if="!loading && projects.length === 0" class="text-gray-600">
          No projects found
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import { getProjects } from './api/projects'

// STATE
const projects = ref([])  // Lege array (gaat gevuld worden)
const loading = ref(false)  // Zijn we aan het laden?
const error = ref(null)  // Error message

// FUNCTIE: Fetch projects van Django
async function loadProjects() {
  loading.value = true
  error.value = null

  try {
    const data = await getProjects()
    projects.value = data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false  // Finally = altijd, loading of error
  }
}

// onMounted = "Als component geladen is, voer dan uit"
onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
</style>