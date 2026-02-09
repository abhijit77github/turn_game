<template>
  <div class="container">
    <div class="card game-card">
      <!-- Timer Line at Top -->
      <TimerLine
        v-if="gameStore.gameStarted && !gameStore.gameEnded && gameStore.isMyTurn"
        :duration="gameStore.turnTime"
        :key="timerKey"
      />
      
      <div class="header">
        <h1>Game in Progress</h1>
        <div class="connection-status" :class="connectionStatus">
          {{ connectionStatusText }}
        </div>
      </div>
      
      <div class="game-info">
        <div class="info-row">
          <div class="info-item">
            <strong>Room:</strong> {{ roomCode }}
          </div>
          <div class="info-item">
            <strong>Turn:</strong> {{ gameStore.turn }} / {{ gameStore.maxTurns }}
          </div>
        </div>
      </div>
      
      <div v-if="!gameStore.gameEnded" class="game-active">
        <!-- Number Picker Game -->
        <div v-if="gameStore.gameType === 'number_picker'">
          <div class="current-turn">
            <h2>Current Player: {{ gameStore.currentPlayer }}</h2>
            <div v-if="gameStore.isMyTurn" class="my-turn-indicator">
              It's your turn!
            </div>
            <TurnTimer
              v-if="gameStore.gameStarted"
              :duration="gameStore.turnTime"
              :key="timerKey"
            />
          </div>
          
          <div class="players-status">
            <h3>Players:</h3>
            <div class="player-tags">
              <div
                v-for="player in gameStore.players"
                :key="player"
                class="player-tag"
                :class="{
                  'active': player === gameStore.currentPlayer,
                  'me': player === username
                }"
              >
                {{ player }}
              </div>
            </div>
          </div>
          
          <div v-if="gameStore.isMyTurn" class="choices-section">
            <h3>Select Your Choice:</h3>
            <div class="choices">
              <button
                v-for="choice in gameStore.choices"
                :key="choice"
                @click="makeChoice(choice)"
                class="choice-btn"
                :class="{ 'positive': choice >= 0, 'negative': choice < 0 }"
              >
                {{ choice > 0 ? '+' : '' }}{{ choice }}
              </button>
            </div>
          </div>
          
          <div v-else class="waiting-message">
            Waiting for {{ gameStore.currentPlayer }} to make a choice...
          </div>
        </div>
        
        <!-- Chain Reaction Game -->
        <div v-else-if="gameStore.gameType === 'chain_reaction'">
          <ChainReactionBoard
            :board="gameStore.board"
            :playerColors="gameStore.playerColors"
            :currentPlayer="gameStore.currentPlayer"
            :turn="gameStore.turn"
            :round="gameStore.round"
            :isMyTurn="gameStore.isMyTurn"
            :explosions="gameStore.explosions"
            :username="username"
            @move="makeChainReactionMove"
          />
        </div>
        
        <!-- Rock Paper Scissors Game -->
        <div v-else>
          <div class="current-turn">
            <h2>Current Player: {{ gameStore.currentPlayer }}</h2>
            <div v-if="gameStore.isMyTurn" class="my-turn-indicator">
              It's your turn!
            </div>
            <TurnTimer
              v-if="gameStore.gameStarted"
              :duration="gameStore.turnTime"
              :key="timerKey"
            />
          </div>
          
          <div v-if="gameStore.isMyTurn" class="choices-section">
            <h3>Select Your Choice:</h3>
            <div class="choices">
              <button
                v-for="choice in gameStore.choices"
                :key="choice"
                @click="makeChoice(choice)"
                class="choice-btn"
              >
                {{ choice }}
              </button>
            </div>
          </div>
          
          <div v-else class="waiting-message">
            Waiting for {{ gameStore.currentPlayer }} to make a choice...
          </div>
        </div>
        
        <button @click="handleExit" class="exit-btn">Exit Game</button>
      </div>
      
      <div v-else class="game-ended">
        <h2>🎉 Game Ended! 🎉</h2>
        <div class="winner-announcement">
          <h3>Winner: {{ gameStore.winner }}</h3>
        </div>
        
        <div class="actions">
          <button
            v-if="gameStore.isCreator && gameStore.canRestart"
            @click="handleRestart"
            class="restart-btn"
          >
            Restart Game
          </button>
          <button @click="handleExit" class="exit-btn">Exit to Home</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGameStore } from '../stores/game'
import TurnTimer from '../components/TurnTimer.vue'
import TimerLine from '../components/TimerLine.vue'
import ChainReactionBoard from '../components/ChainReactionBoard.vue'

export default {
  name: 'Game',
  components: {
    TurnTimer,
    TimerLine,
    ChainReactionBoard
  },
  setup() {
    const router = useRouter()
    const route = useRoute()
    const authStore = useAuthStore()
    const gameStore = useGameStore()
    
    const roomCode = ref(route.params.code.toUpperCase())
    const timerKey = ref(0)
    
    const username = computed(() => authStore.getUsername)
    const connectionStatus = computed(() => gameStore.connectionStatus)
    
    const connectionStatusText = computed(() => {
      const statuses = {
        'connected': '● Connected',
        'connecting': '○ Connecting...',
        'disconnected': '○ Reconnecting...',
        'error': '○ Connection Error'
      }
      return statuses[connectionStatus.value] || '○ Unknown'
    })
    
    const makeChoice = (choice) => {
      gameStore.makeChoice(choice)
    }
    
    const makeChainReactionMove = (coordinates) => {
      gameStore.makeChoice(coordinates)
    }
    
    const handleExit = () => {
      gameStore.exitGame()
      router.push('/home')
    }
    
    const handleRestart = () => {
      gameStore.restartGame()
    }
    
    // Watch for turn changes to reset timer
    watch(() => gameStore.turn, () => {
      timerKey.value++
    })
    
    onMounted(() => {
      // Connect to WebSocket if not connected
      if (!gameStore.ws || gameStore.ws.readyState !== WebSocket.OPEN) {
        gameStore.connectWebSocket(roomCode.value, authStore.getUsername)
      }
    })
    
    return {
      roomCode,
      gameStore,
      username,
      connectionStatus,
      connectionStatusText,
      timerKey,
      makeChoice,
      makeChainReactionMove,
      handleExit,
      handleRestart
    }
  }
}
</script>

<style scoped>
.container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
}

.game-card {
  width: 100%;
  max-width: 900px;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

h1 {
  color: #333;
  margin: 0;
}

.connection-status {
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: bold;
}

.connection-status.connected {
  background: #d4edda;
  color: #155724;
}

.connection-status.connecting,
.connection-status.disconnected {
  background: #fff3cd;
  color: #856404;
}

.connection-status.error {
  background: #f8d7da;
  color: #721c24;
}

.game-info {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.info-item {
  font-size: 18px;
}

.current-turn {
  text-align: center;
  margin-bottom: 30px;
}

.current-turn h2 {
  color: #667eea;
  margin-bottom: 15px;
}

.my-turn-indicator {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 15px;
  border-radius: 8px;
  font-size: 20px;
  font-weight: bold;
  margin: 20px 0;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.players-status {
  margin: 30px 0;
}

.players-status h3 {
  color: #555;
  margin-bottom: 15px;
}

.player-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.player-tag {
  padding: 10px 20px;
  border-radius: 20px;
  background: #f0f0f0;
  font-weight: 500;
}

.player-tag.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  animation: glow 1.5s infinite;
}

.player-tag.me {
  border: 2px solid #667eea;
}

@keyframes glow {
  0%, 100% {
    box-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
  }
  50% {
    box-shadow: 0 0 20px rgba(102, 126, 234, 0.8);
  }
}

.choices-section {
  margin: 30px 0;
  padding: 30px;
  background: #f8f9fa;
  border-radius: 12px;
}

.choices-section h3 {
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}

.choices {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 15px;
}

.choice-btn {
  padding: 30px;
  font-size: 28px;
  font-weight: bold;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.choice-btn.positive {
  background: #27ae60;
  color: white;
}

.choice-btn.positive:hover {
  background: #229954;
  transform: translateY(-5px) scale(1.05);
}

.choice-btn.negative {
  background: #e74c3c;
  color: white;
}

.choice-btn.negative:hover {
  background: #c0392b;
  transform: translateY(-5px) scale(1.05);
}

.waiting-message {
  text-align: center;
  padding: 40px;
  font-size: 20px;
  color: #666;
  font-style: italic;
}

.exit-btn {
  background: #95a5a6;
  color: white;
  width: 100%;
  margin-top: 30px;
  padding: 15px;
  font-size: 16px;
}

.exit-btn:hover {
  background: #7f8c8d;
}

.game-ended {
  text-align: center;
  padding: 40px 0;
}

.game-ended h2 {
  color: #667eea;
  font-size: 36px;
  margin-bottom: 30px;
}

.winner-announcement {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 40px;
  border-radius: 12px;
  margin: 30px 0;
}

.winner-announcement h3 {
  font-size: 32px;
  margin: 0;
}

.actions {
  display: flex;
  gap: 15px;
  margin-top: 30px;
}

.actions button {
  flex: 1;
  padding: 15px;
  font-size: 18px;
  font-weight: bold;
}

.restart-btn {
  background: #27ae60;
  color: white;
}

.restart-btn:hover {
  background: #229954;
}
</style>
