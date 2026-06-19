import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
  { path: '/projects', name: 'Projects', component: () => import('@/views/Projects.vue') },
  { path: '/weekstaat', name: 'Weekstaat', component: () => import('@/views/Weekstaat.vue') },
  { path: '/stats', name: 'Stats', component: () => import('@/views/Stats.vue') },
  { path: '/rules', name: 'Rules', component: () => import('@/views/Rules.vue') },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;