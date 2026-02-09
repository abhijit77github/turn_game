<template>
  <div class="turn-timer">
    <div class="timer-label">Time Remaining</div>
    <div class="timer-display">
      <svg class="timer-circle" :width="size" :height="size">
        <circle
          class="timer-background"
          :cx="size / 2"
          :cy="size / 2"
          :r="radius"
        />
        <circle
          class="timer-progress"
          :cx="size / 2"
          :cy="size / 2"
          :r="radius"
          :style="progressStyle"
        />
      </svg>
      <div class="timer-text">{{ timeLeft }}s</div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'

export default {
  name: 'TurnTimer',
  props: {
    duration: {
      type: Number,
      default: 10
    }
  },
  setup(props) {
    const timeLeft = ref(props.duration)
    const size = 150
    const radius = 60
    const circumference = 2 * Math.PI * radius
    
    let interval = null
    
    const progressStyle = computed(() => {
      const progress = timeLeft.value / props.duration
      const offset = circumference * (1 - progress)
      return {
        strokeDasharray: `${circumference} ${circumference}`,
        strokeDashoffset: offset
      }
    })
    
    onMounted(() => {
      interval = setInterval(() => {
        if (timeLeft.value > 0) {
          timeLeft.value--
        } else {
          clearInterval(interval)
        }
      }, 1000)
    })
    
    onUnmounted(() => {
      if (interval) {
        clearInterval(interval)
      }
    })
    
    return {
      timeLeft,
      size,
      radius,
      progressStyle
    }
  }
}
</script>

<style scoped>
.turn-timer {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 20px 0;
}

.timer-label {
  font-size: 16px;
  color: #666;
  margin-bottom: 10px;
  font-weight: 500;
}

.timer-display {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.timer-circle {
  transform: rotate(-90deg);
}

.timer-background {
  fill: none;
  stroke: #e0e0e0;
  stroke-width: 8;
}

.timer-progress {
  fill: none;
  stroke: #667eea;
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dashoffset 1s linear;
}

.timer-text {
  position: absolute;
  font-size: 32px;
  font-weight: bold;
  color: #667eea;
}
</style>
