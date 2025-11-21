<template>
  <div class="flex items-center justify-center" :class="containerClass">
    <div class="relative">
      <div
        class="w-12 h-12 rounded-full border-4 border-gray-200"
        :class="spinnerClass"
      ></div>
      <div
        class="absolute top-0 left-0 w-12 h-12 rounded-full border-4 border-transparent border-t-primary-600 animate-spin"
      ></div>
    </div>
    <p v-if="text" class="ml-4 text-gray-600">{{ text }}</p>
  </div>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    default: ''
  },
  containerClass: {
    type: String,
    default: 'py-12'
  },
  spinnerClass: {
    type: String,
    default: ''
  }
})
</script>
