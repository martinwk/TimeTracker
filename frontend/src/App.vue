<script setup>
import { ref } from 'vue';
import Sidebar from './components/Sidebar.vue';

const isSidebarOpen = ref(true);
</script>

<template>
  <div class="flex h-screen bg-gray-100">
    <Sidebar :is-open="isSidebarOpen" @toggle="isSidebarOpen = !isSidebarOpen" />
    <main
      class="flex-1 overflow-auto transition-all duration-300"
      :class="isSidebarOpen ? 'ml-64' : 'ml-0'"
    >
      <router-view />
    </main>
  </div>
</template>