<script setup>
defineProps({
  isOpen: Boolean,
});

const emit = defineEmits(['toggle']);

const navItems = [
  { name: 'Dashboard', path: '/' },
  { name: 'Projects', path: '/projects' },
  { name: 'Stats', path: '/stats' },
];
</script>

<template>
  <aside
    class="fixed left-0 top-0 h-full w-64 bg-white shadow-md transform transition-transform duration-300 ease-in-out"
    :class="isOpen ? 'translate-x-0' : '-translate-x-full'"
  >
    <div class="p-4 border-b">
      <button
        @click="emit('toggle')"
        class="p-2 rounded-md hover:bg-gray-100 md:hidden"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
      <h1 class="text-xl font-bold hidden md:block">Tijdregistratie</h1>
    </div>
    <nav class="p-4">
      <ul class="space-y-2">
        <li v-for="item in navItems" :key="item.path">
          <router-link
            :to="item.path"
            class="flex items-center p-2 rounded-md hover:bg-gray-100"
            active-class="bg-blue-50 text-blue-600"
          >
            {{ item.name }}
          </router-link>
        </li>
      </ul>
    </nav>
  </aside>
</template>