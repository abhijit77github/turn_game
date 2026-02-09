<template>
  <div class="timer-line-container">
    <div class="timer-line" :style="{ width: progressPercent + '%' }"></div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'

export default {
  name: 'TimerLine',
  props: {
    duration: {
      type: Number,
      required: true,
      default: 10
    }
  },
  setup(props) {
    const progressPercent = ref(100)
    let interval = null
    let elapsedTime = 0

    onMounted(() => {
      elapsedTime = 0
      progressPercent.value = 100

      interval = setInterval(() => {
        elapsedTime += 0.1
        const remaining = Math.max(0, props.duration - elapsedTime)
        progressPercent.value = (remaining / props.duration) * 100
        
        if (elapsedTime >= props.duration) {
          clearInterval(interval)
        }
      }, 100)
    })

    onUnmounted(() => {
      if (interval) {
        clearInterval(interval)
      }
    })

    return {
      progressPercent
    }
  }
}
</script>

<style scoped>
.timer-line-container {
  width: 100%;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1);
}

.timer-line {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #06b6d4);
  border-radius: 3px;
  transition: width 0.1s linear;
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.5);
}
</style>
