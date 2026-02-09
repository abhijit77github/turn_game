<template>
  <div class="chain-reaction-container">
    <div class="game-info">
      <div class="info-item">Round: {{ round }} | Turn: {{ turn }}</div>
      <div class="info-item" :class="{ 'my-turn': isMyTurn }">
        {{ username }}
      </div>
    </div>
    
    <!-- Game Board as SVG -->
    <svg 
      ref="boardRef"
      class="board-svg"
      :class="{ 'board-disabled': !isMyTurn }"
      :width="CELL_SIZE * 6 + 40" 
      :height="CELL_SIZE * 10 + 40"
      viewBox="0 0 360 640"
    >
      <!-- Background -->
      <rect x="0" y="0" width="360" height="640" fill="#f9f9f9" stroke="#333" stroke-width="3"/>
      
      <!-- Grid cells -->
      <g v-for="(row, y) in board" :key="`row-${y}`">
        <g v-for="(cell, x) in row" :key="`cell-${x}-${y}`">
          <!-- Cell rectangle -->
          <rect
            :x="20 + x * CELL_SIZE"
            :y="20 + y * CELL_SIZE"
            :width="CELL_SIZE - 4"
            :height="CELL_SIZE - 4"
            :class="{
              'svg-cell': true,
              'svg-cell-empty': cell.balls.length === 0,
              'svg-cell-has-balls': cell.balls.length > 0,
              'svg-cell-unstable': isUnstable(x, y),
              'svg-cell-exploding': isExploding(x, y)
            }"
            @click="makeMove(x, y)"
            rx="8"
          />
          
          <!-- Balls in cell -->
          <g v-if="cell.balls.length > 0" class="svg-balls-group" @click="makeMove(x, y)">
            <circle
              v-for="(color, idx) in cell.balls.slice(0, 3)"
              :key="`ball-${idx}`"
              :cx="20 + x * CELL_SIZE + CELL_SIZE/2 + getBallOffsetX(idx, cell.balls.length)"
              :cy="20 + y * CELL_SIZE + CELL_SIZE/2 + getBallOffsetY(idx, cell.balls.length)"
              :r="10"
              :fill="color"
              :class="{ 'svg-ball-rotating': isUnstable(x, y) }"
              class="svg-ball"
              style="pointer-events: none"
            />
            
            <!-- Ball count indicator if more than 3 -->
            <text
              v-if="cell.balls.length > 3"
              :x="20 + x * CELL_SIZE + CELL_SIZE - 10"
              :y="20 + y * CELL_SIZE + CELL_SIZE - 5"
              class="svg-ball-count"
              text-anchor="middle"
            >
              +{{ cell.balls.length - 3 }}
            </text>
          </g>
        </g>
      </g>
      
      <!-- Flying balls with animation -->
      <g>
        <circle
          v-for="(flyingBall, idx) in flyingBalls"
          :key="`flying-${idx}`"
          :cx="flyingBall.x"
          :cy="flyingBall.y"
          r="10"
          :fill="flyingBall.color"
          class="svg-flying-ball"
        >
          <animateTransform
            attributeName="transform"
            type="translate"
            :from="`0 0`"
            :to="`${flyingBall.targetX - flyingBall.x} ${flyingBall.targetY - flyingBall.y}`"
            dur="1.5s"
            fill="freeze"
          />
          <animate
            attributeName="opacity"
            from="1"
            to="0"
            dur="1.5s"
            fill="freeze"
          />
          <animate
            attributeName="r"
            values="10;12;8"
            dur="1.5s"
            fill="freeze"
          />
        </circle>
      </g>
    </svg>
    
    <!-- Color Legend -->
    <div class="legend">
      <div
        v-for="(color, player) in playerColors"
        :key="player"
        class="legend-item"
        :class="{ 'active': player === currentPlayer }"
      >
        <div class="color-dot" :style="{ backgroundColor: color }"></div>
        {{ player }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, nextTick } from 'vue'

export default {
  name: 'ChainReactionGame',
  props: {
    board: {
      type: Array,
      required: true
    },
    playerColors: {
      type: Object,
      required: true
    },
    currentPlayer: {
      type: String,
      required: true
    },
    turn: {
      type: Number,
      required: true
    },
    round: {
      type: Number,
      required: true
    },
    isMyTurn: {
      type: Boolean,
      required: true
    },
    explosions: {
      type: Array,
      default: () => []
    },
    username: {
      type: String,
      required: true
    }
  },
  emits: ['move'],
  setup(props, { emit }) {
    const boardRef = ref(null)
    const flyingBalls = ref([])
    const CELL_SIZE = 56 // SVG units
    
    const makeMove = (x, y) => {
      if (props.isMyTurn) {
        emit('move', [x, y])
      }
    }
    
    const isExploding = (x, y) => {
      if (!props.explosions || props.explosions.length === 0) return false
      // Only check the current (first) explosion in the queue
      const event = props.explosions[0]
      return event.type === 'explosion' && event.x === x && event.y === y
    }
    
    const getAdjacentCellsCount = (x, y) => {
      let count = 0
      // Up, Down, Left, Right
      if (y > 0) count++ // Up
      if (y < 9) count++ // Down (board height is 10, so max y is 9)
      if (x > 0) count++ // Left
      if (x < 5) count++ // Right (board width is 6, so max x is 5)
      return count
    }
    
    const isUnstable = (x, y) => {
      const cell = props.board[y][x]
      const adjacentCount = getAdjacentCellsCount(x, y)
      const stabilityLimit = adjacentCount
      return cell.balls.length === stabilityLimit - 1
    }
    
    const getBallOffsetX = (index, totalBalls) => {
      // Position balls with circular arrangement for SVG
      if (totalBalls === 1) return 0
      const angle = (index / totalBalls) * Math.PI * 2
      const radius = 8
      return Math.cos(angle) * radius
    }
    
    const getBallOffsetY = (index, totalBalls) => {
      // Position balls with circular arrangement for SVG
      if (totalBalls === 1) return 0
      const angle = (index / totalBalls) * Math.PI * 2
      const radius = 8
      return Math.sin(angle) * radius
    }
    
    const getCellCenter = (x, y) => {
      // Return SVG coordinates for cell center
      return {
        x: 20 + x * CELL_SIZE + CELL_SIZE / 2,
        y: 20 + y * CELL_SIZE + CELL_SIZE / 2
      }
    }
    
    const getNeighbors = (x, y) => {
      const neighbors = []
      if (y > 0) neighbors.push({ x, y: y - 1 }) // Up
      if (y < 9) neighbors.push({ x, y: y + 1 }) // Down
      if (x > 0) neighbors.push({ x: x - 1, y }) // Left
      if (x < 5) neighbors.push({ x: x + 1, y }) // Right
      return neighbors
    }
    
    // Watch for explosions and create flying balls
    watch(() => props.explosions, (newExplosions) => {
      if (!newExplosions || newExplosions.length === 0) {
        flyingBalls.value = []
        return
      }
      
      // Only process the first (current) explosion
      const event = newExplosions[0]
      
      if (event.type === 'spread') {
        requestAnimationFrame(() => {
          const sourcePos = getCellCenter(event.from_x, event.from_y)
          const targetPos = getCellCenter(event.to_x, event.to_y)
          
          if (sourcePos.x > 0 && sourcePos.y > 0 && targetPos.x > 0 && targetPos.y > 0) {
            // Replace flying balls with current one (only one ball flying at a time)
            flyingBalls.value = [{
              x: sourcePos.x,
              y: sourcePos.y,
              targetX: targetPos.x,
              targetY: targetPos.y,
              color: event.color
            }]
          }
        })
      } else {
        flyingBalls.value = []
      }
    })
    
    return {
      boardRef,
      flyingBalls,
      CELL_SIZE,
      makeMove,
      isUnstable,
      isExploding,
      getBallOffsetX,
      getBallOffsetY
    }
  }
}
</script>

<style scoped>
.chain-reaction-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 20px;
}

.game-info {
  display: flex;
  gap: 20px;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
}

.info-item {
  padding: 10px 20px;
  background: #f0f0f0;
  border-radius: 5px;
  transition: all 0.3s ease;
}

.info-item.my-turn {
  background: #22c55e;
  color: white;
  font-weight: bold;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.5);
}

.board {
  display: inline-block;
  border: 3px solid #333;
  background: #f9f9f9;
  gap: 2px;
  padding: 10px;
  position: relative;
}

.row {
  display: flex;
  gap: 2px;
  margin-bottom: 2px;
}

.cell {
  width: 50px;
  height: 50px;
  border: 2px solid #ddd;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #ffffff;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.cell:hover {
  transform: scale(1.05);
  border-color: #667eea;
  box-shadow: 0 0 10px rgba(102, 126, 234, 0.3);
}

.cell.empty {
  background: linear-gradient(135deg, #f5f5f5, #ffffff);
}

.cell.has-balls {
  background: linear-gradient(135deg, #f0f0f0, #ffffff);
  border-color: #999;
}

.cell.unstable {
  animation: pulse-warning 0.6s ease-in-out infinite;
  background: linear-gradient(135deg, #ffe6e6, #fff0f0);
  border-color: #ff6b6b;
}

.cell.exploding {
  animation: explode 2s ease-out;
  background: linear-gradient(135deg, #ffcccc, #ffe6e6);
  border-color: #ff4444;
}

@keyframes pulse-warning {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(255, 107, 107, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(255, 107, 107, 0);
  }
}

@keyframes explode {
  0% {
    transform: scale(1);
    background: linear-gradient(135deg, #ffaaaa, #ffcccc);
    box-shadow: 0 0 0 rgba(255, 68, 68, 0);
  }
  25% {
    transform: scale(1.3);
    box-shadow: 0 0 30px rgba(255, 68, 68, 0.8);
  }
  50% {
    transform: scale(1.4);
    box-shadow: 0 0 40px rgba(255, 68, 68, 1);
    opacity: 0.8;
  }
  75% {
    transform: scale(1.2);
    box-shadow: 0 0 20px rgba(255, 68, 68, 0.6);
  }
  100% {
    transform: scale(1);
    background: linear-gradient(135deg, #ffcccc, #ffe6e6);
    box-shadow: 0 0 0 rgba(255, 68, 68, 0);
  }
}

.balls-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ball {
  position: absolute;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  box-shadow: inset -2px -2px 4px rgba(0, 0, 0, 0.3), inset 2px 2px 4px rgba(255, 255, 255, 0.5);
  transition: all 0.3s ease;
}

.ball.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  0% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-3px) rotate(180deg);
  }
  100% {
    transform: translateY(0) rotate(360deg);
  }
}

.ball-count {
  position: absolute;
  bottom: 2px;
  right: 2px;
  font-size: 10px;
  font-weight: bold;
  color: white;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 4px;
  border-radius: 3px;
}

.legend {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  justify-content: center;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 15px;
  border: 2px solid #ddd;
  border-radius: 20px;
  background: white;
  transition: all 0.3s ease;
}

.legend-item.active {
  border-color: #22c55e;
  background: #dcfce7;
  font-weight: bold;
  color: #15803d;
}

.color-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  box-shadow: 0 0 3px rgba(0, 0, 0, 0.2);
}

/* SVG Board Styles */
.board-svg {
  display: block;
  margin: 0 auto;
  border-radius: 10px;
}

.svg-cell {
  fill: #ffffff;
  stroke: #ddd;
  stroke-width: 2;
  cursor: pointer;
  transition: all 0.3s ease;
}

.board-disabled .svg-cell {
  cursor: not-allowed;
  opacity: 0.7;
}

.svg-cell:hover {
  stroke: #667eea;
  stroke-width: 3;
  filter: drop-shadow(0 0 10px rgba(102, 126, 234, 0.3));
}

.board-disabled .svg-cell:hover {
  stroke: #ddd;
  stroke-width: 2;
  filter: none;
}

.svg-cell-empty {
  fill: #f5f5f5;
}

.svg-cell-has-balls {
  fill: #f0f0f0;
  stroke: #999;
}

.svg-cell-unstable {
  animation: svg-pulse-warning 0.6s ease-in-out infinite;
  fill: #ffe6e6;
  stroke: #ff6b6b;
}

.svg-cell-exploding {
  animation: svg-explode 1.5s ease-out;
  fill: #ffcccc;
  stroke: #ff4444;
  transform-origin: center;
}

@keyframes svg-pulse-warning {
  0%, 100% {
    filter: drop-shadow(0 0 0 rgba(255, 107, 107, 0.4));
  }
  50% {
    filter: drop-shadow(0 0 8px rgba(255, 107, 107, 0.8));
  }
}

@keyframes svg-explode {
  0% {
    filter: drop-shadow(0 0 0 rgba(255, 68, 68, 0));
  }
  25% {
    filter: drop-shadow(0 0 30px rgba(255, 68, 68, 0.8));
  }
  50% {
    filter: drop-shadow(0 0 40px rgba(255, 68, 68, 1));
    opacity: 0.8;
  }
  75% {
    filter: drop-shadow(0 0 20px rgba(255, 68, 68, 0.6));
  }
  100% {
    filter: drop-shadow(0 0 0 rgba(255, 68, 68, 0));
  }
}

.svg-ball {
  filter: drop-shadow(2px 2px 4px rgba(0, 0, 0, 0.3));
  transition: all 0.3s ease;
}

.svg-ball-rotating {
  animation: svg-rotate 1s linear infinite;
}

@keyframes svg-rotate {
  0% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
  100% {
    transform: translateY(0);
  }
}

.svg-ball-count {
  font-size: 10px;
  font-weight: bold;
  fill: white;
  filter: drop-shadow(1px 1px 2px rgba(0, 0, 0, 0.5));
}

.svg-flying-ball {
  filter: drop-shadow(0 0 15px rgba(255, 255, 255, 0.8));
}
</style>
