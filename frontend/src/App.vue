<template>
  <div class="flex">
    <!-- Sidebar links -->
    <Sidebar />

    <!-- Inhoud rechts -->
    <main class="flex-1 bg-gray-100 p-8">
      <h1 class="text-4xl font-bold text-blue-600">
        🎉 TimeTracker Vue App
      </h1>
      <p class="text-gray-700 mt-4">
        Hello World! Ik ben aan het leren met Vue.
      </p>

      <!-- NIEUWE CODE: Counter -->
      <div class="mt-8 bg-white p-6 rounded-lg shadow">
        <h2 class="text-2xl font-bold mb-4">Counter Example</h2>

        <!-- Toon het getal -->
        <p class="text-xl mb-4">
          Counter: <span class="font-bold text-blue-600">{{ count }}</span>
        </p>

        <!-- Knoppen om het getal te veranderen -->
        <div class="flex gap-4">
          <button
            @click="count = count + 1"
            class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            + Increment
          </button>
          <button
            @click="count = count - 1"
            class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            - Decrement
          </button>
          <button
            @click="count = 0"
            class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Reset
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'  // ← Import ref
import Sidebar from './components/Sidebar.vue'

// STATE: een getal dat kan veranderen
const count = ref(0)
</script>

<style scoped>
</style>