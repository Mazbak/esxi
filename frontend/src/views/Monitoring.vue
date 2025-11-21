<template>
  <div class="space-y-6">
    <!--Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Monitoring & Santé</h1>
        <p class="mt-1 text-sm text-gray-500">Surveillez l'état de santé de votre système de backup</p>
      </div>
    </div>

    <!-- Health Monitoring Dashboard -->
    <HealthMonitoringDashboard />
  </div>
</template>

<script setup>
import HealthMonitoringDashboard from '@/components/monitoring/HealthMonitoringDashboard.vue'
</script>
