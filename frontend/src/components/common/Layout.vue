<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50">
    <!-- Sidebar -->
    <Sidebar :is-open="sidebarOpen" @close="sidebarOpen = false" />

    <!-- Main Content -->
    <div class="lg:pl-72">
      <!-- Header -->
      <Header @toggle-sidebar="sidebarOpen = !sidebarOpen" />

      <!-- Page Content -->
      <main class="py-8 px-4 sm:px-6 lg:px-8 animate-fade-in">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const sidebarOpen = ref(false)
</script>
