<template>
  <div class="relative group">
    <!-- Card avec effet glassmorphism -->
    <div :class="cardClass" class="relative overflow-hidden">
      <!-- Decorative gradient background -->
      <div :class="gradientBgClass" class="absolute top-0 right-0 w-32 h-32 blur-3xl opacity-20 group-hover:opacity-30 transition-opacity duration-500"></div>

      <!-- Border decoration -->
      <div :class="borderClass" class="absolute inset-x-0 top-0 h-1"></div>

      <!-- Content -->
      <div class="relative z-10 flex items-center justify-between">
        <div class="flex-1">
          <p class="text-sm font-semibold text-gray-600 uppercase tracking-wide">{{ title }}</p>
          <p class="mt-3 text-4xl font-bold bg-gradient-to-r bg-clip-text text-transparent" :class="textGradientClass">
            {{ value }}
          </p>
          <p v-if="subtitle" class="mt-2 text-sm text-gray-500 font-medium">{{ subtitle }}</p>
        </div>

        <!-- Icon with animation -->
        <div :class="iconBgClass" class="relative p-4 rounded-2xl shadow-lg transform transition-all duration-300 group-hover:scale-110 group-hover:rotate-6">
          <div class="absolute inset-0 bg-white/50 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300"></div>
          <component :is="iconComponent" class="relative w-10 h-10" :class="iconColorClass" />
        </div>
      </div>

      <!-- Trend indicator -->
      <div v-if="trend" class="relative z-10 mt-6 pt-4 border-t border-gray-100 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <div :class="trendBgClass" class="px-3 py-1 rounded-full flex items-center space-x-1">
            <svg v-if="trendDirection === 'up'" class="w-4 h-4" :class="trendClass" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clip-rule="evenodd" />
            </svg>
            <svg v-else class="w-4 h-4" :class="trendClass" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M12 13a1 1 0 100 2h5a1 1 0 001-1V9a1 1 0 10-2 0v2.586l-4.293-4.293a1 1 0 00-1.414 0L8 9.586 3.707 5.293a1 1 0 00-1.414 1.414l5 5a1 1 0 001.414 0L11 9.414 14.586 13H12z" clip-rule="evenodd" />
            </svg>
            <span :class="trendClass" class="text-sm font-bold">{{ trend }}</span>
          </div>
          <span class="text-sm text-gray-600 font-medium">{{ trendLabel }}</span>
        </div>
      </div>

      <!-- Hover effect overlay -->
      <div class="absolute inset-0 bg-gradient-to-br from-white/0 via-white/0 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
    </div>

    <!-- Shadow effect on hover -->
    <div :class="shadowClass" class="absolute inset-0 -z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-xl"></div>
  </div>
</template>

<script setup>
import { computed, h } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  },
  icon: {
    type: String,
    default: 'chart'
  },
  color: {
    type: String,
    default: 'blue',
    validator: (value) => ['blue', 'green', 'red', 'yellow', 'purple', 'indigo', 'pink'].includes(value)
  },
  trend: {
    type: String,
    default: ''
  },
  trendLabel: {
    type: String,
    default: ''
  },
  trendDirection: {
    type: String,
    default: 'up',
    validator: (value) => ['up', 'down'].includes(value)
  }
})

const cardClass = computed(() => {
  return 'card-stats p-6 transform transition-all duration-300 group-hover:-translate-y-2'
})

const gradientBgClass = computed(() => {
  const gradients = {
    blue: 'bg-gradient-to-br from-blue-400 to-cyan-400',
    green: 'bg-gradient-to-br from-green-400 to-emerald-400',
    red: 'bg-gradient-to-br from-red-400 to-pink-400',
    yellow: 'bg-gradient-to-br from-yellow-400 to-orange-400',
    purple: 'bg-gradient-to-br from-purple-400 to-violet-400',
    indigo: 'bg-gradient-to-br from-indigo-400 to-blue-400',
    pink: 'bg-gradient-to-br from-pink-400 to-rose-400'
  }
  return gradients[props.color]
})

const borderClass = computed(() => {
  const borders = {
    blue: 'bg-gradient-to-r from-blue-500 to-cyan-500',
    green: 'bg-gradient-to-r from-green-500 to-emerald-500',
    red: 'bg-gradient-to-r from-red-500 to-pink-500',
    yellow: 'bg-gradient-to-r from-yellow-500 to-orange-500',
    purple: 'bg-gradient-to-r from-purple-500 to-violet-500',
    indigo: 'bg-gradient-to-r from-indigo-500 to-blue-500',
    pink: 'bg-gradient-to-r from-pink-500 to-rose-500'
  }
  return borders[props.color]
})

const textGradientClass = computed(() => {
  const gradients = {
    blue: 'from-blue-600 to-cyan-600',
    green: 'from-green-600 to-emerald-600',
    red: 'from-red-600 to-pink-600',
    yellow: 'from-yellow-600 to-orange-600',
    purple: 'from-purple-600 to-violet-600',
    indigo: 'from-indigo-600 to-blue-600',
    pink: 'from-pink-600 to-rose-600'
  }
  return gradients[props.color]
})

const iconBgClass = computed(() => {
  const colors = {
    blue: 'bg-gradient-to-br from-blue-500 to-cyan-600',
    green: 'bg-gradient-to-br from-green-500 to-emerald-600',
    red: 'bg-gradient-to-br from-red-500 to-pink-600',
    yellow: 'bg-gradient-to-br from-yellow-500 to-orange-600',
    purple: 'bg-gradient-to-br from-purple-500 to-violet-600',
    indigo: 'bg-gradient-to-br from-indigo-500 to-blue-600',
    pink: 'bg-gradient-to-br from-pink-500 to-rose-600'
  }
  return colors[props.color]
})

const iconColorClass = computed(() => {
  return 'text-white'
})

const shadowClass = computed(() => {
  const shadows = {
    blue: 'bg-blue-400',
    green: 'bg-green-400',
    red: 'bg-red-400',
    yellow: 'bg-yellow-400',
    purple: 'bg-purple-400',
    indigo: 'bg-indigo-400',
    pink: 'bg-pink-400'
  }
  return shadows[props.color]
})

const trendClass = computed(() => {
  return props.trendDirection === 'up' ? 'text-green-600' : 'text-red-600'
})

const trendBgClass = computed(() => {
  return props.trendDirection === 'up' ? 'bg-green-100' : 'bg-red-100'
})

const iconComponent = computed(() => {
  const icons = {
    server: IconServer,
    vm: IconVM,
    backup: IconBackup,
    chart: IconChart,
    clock: IconClock,
    check: IconCheck,
    warning: IconWarning
  }
  return icons[props.icon] || icons.chart
})

// Icon components using render functions
const IconServer = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2.5' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01' })
  ])
}

const IconVM = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2.5' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z' })
  ])
}

const IconBackup = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2.5' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12' })
  ])
}

const IconChart = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2.5' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' })
  ])
}

const IconClock = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2.5' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' })
  ])
}

const IconCheck = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2.5' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' })
  ])
}

const IconWarning = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2.5' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' })
  ])
}
</script>
