<template>
  <div class="container">
    <div class="card">
      <div class="header">
        <h1>Room: {{ roomCode }}</h1>
        <div class="connection-status" :class="connectionStatus">
          {{ connectionStatusText }}
        </div>
      </div>
      
      <div class="room-info">
        <div class="info-item">
          <strong>Room Code:</strong>
          <span class="room-code-display">{{ roomCode }}</span>
        </div>
        <div class="info-item">
          <strong>Creator:</strong> {{ gameStore.creator }}
        </div>
        <div class="info-item">
          <strong>Players:</strong> {{ gameStore.players.length }} / {{ maxPlayers }}
        </div>
      </div>
      
      <div class="players-list">
        <h3>Players in Room:</h3>
        <div class="players">
          <div
            v-for="player in gameStore.players"
            :key="player"
            class="player-item"
            :class="{ 'is-creator': player === gameStore.creator }"
          >
            {{ player }}
            <span v-if="player === gameStore.creator" class="badge">Creator</span>
          </div>
        </div>
      </div>
      
      <div class="actions">
        <button
          v-if="gameStore.isCreator"
          @click="handleStartGame"
          :disabled="!canStart || gameStore.gameStarted"
          class="start-btn"
        >
          {{ gameStore.gameStarted ? 'Game Started' : 'Start Game' }}
        </button>
        
        <button @click="handleExit" class="exit-btn">
          Exit Room
        </button>
      </div>
      
      <div v-if="!canStart && gameStore.isCreator" class="info-message">
        Need at least {{ minPlayers }} players to start the game
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGameStore } from '../stores/game'

export default {
  name: 'Room',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const authStore = useAuthStore()
    const gameStore = useGameStore()
    
    const roomCode = ref(route.params.code.toUpperCase())
    const maxPlayers = ref(6)
    const minPlayers = ref(2)
    
    const connectionStatus = computed(() => gameStore.connectionStatus)
    
    const connectionStatusText = computed(() => {
      const statuses = {
        'connected': '● Connected',
        'connecting': '○ Connecting...',
        'disconnected': '○ Disconnected',
        'error': '○ Connection Error'
      }
      return statuses[connectionStatus.value] || '○ Unknown'
    })
    
    const canStart = computed(() => {
      return gameStore.players.length >= minPlayers.value &&
             gameStore.players.length <= maxPlayers.value
    })
    
    const handleStartGame = () => {
      gameStore.startGame()
      router.push(`/game/${roomCode.value}`)
    }
    
    const handleExit = () => {
      gameStore.exitGame()
      router.push('/home')
    }
    
    onMounted(() => {
      // Connect to WebSocket
      gameStore.connectWebSocket(roomCode.value, authStore.getUsername)
      
      // Watch for game started
      const checkGameStarted = setInterval(() => {
        if (gameStore.gameStarted) {
          router.push(`/game/${roomCode.value}`)
          clearInterval(checkGameStarted)
        }
      }, 500)
      
      // Clean up on unmount
      onUnmounted(() => {
        clearInterval(checkGameStarted)
      })
    })
    
    return {
      roomCode,
      gameStore,
      maxPlayers,
      minPlayers,
      connectionStatus,
      connectionStatusText,
      canStart,
      handleStartGame,
      handleExit
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

.connection-status.connecting {
  background: #fff3cd;
  color: #856404;
}

.connection-status.disconnected,
.connection-status.error {
  background: #f8d7da;
  color: #721c24;
}

.room-info {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.info-item {
  margin: 10px 0;
  font-size: 16px;
}

.room-code-display {
  font-weight: bold;
  font-size: 24px;
  color: #667eea;
  letter-spacing: 3px;
  margin-left: 10px;
}

.players-list {
  margin: 30px 0;
}

.players-list h3 {
  color: #555;
  margin-bottom: 15px;
}

.players {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.player-item {
  background: #f0f0f0;
  padding: 15px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
}

.player-item.is-creator {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.badge {
  background: rgba(255, 255, 255, 0.3);
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
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

.start-btn {
  background: #27ae60;
  color: white;
}

.start-btn:hover:not(:disabled) {
  background: #229954;
}

.exit-btn {
  background: #e74c3c;
  color: white;
}

.exit-btn:hover {
  background: #c0392b;
}

.info-message {
  margin-top: 20px;
  padding: 15px;
  background: #fff3cd;
  color: #856404;
  border-radius: 8px;
  text-align: center;
}
</style>
