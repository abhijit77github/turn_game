<template>
  <div class="container">
    <div class="card">
      <div class="header">
        <h1>Welcome, {{ username }}!</h1>
        <button @click="handleLogout" class="logout-btn">Logout</button>
      </div>
      
      <div class="actions">
        <div class="action-card">
          <h2>Create a Room</h2>
          <p>Start a new game and invite your friends</p>
          
          <!-- Game Selection -->
          <div class="game-selection">
            <label for="gameType">Choose Game:</label>
            <select v-model="selectedGame" id="gameType" class="game-select">
              <option v-for="game in availableGames" :key="game.name" :value="game.name">
                {{ game.display_name }}
              </option>
            </select>
          </div>
          
          <button @click="handleCreateRoom" :disabled="loading || !selectedGame">
            {{ loading ? 'Creating...' : 'Create Room' }}
          </button>
        </div>
        
        <div class="divider">OR</div>
        
        <div class="action-card">
          <h2>Join a Room</h2>
          <p>Enter a room code to join an existing game</p>
          <input
            v-model="roomCode"
            type="text"
            placeholder="Enter Room Code"
            maxlength="6"
            @input="roomCode = roomCode.toUpperCase()"
          />
          <button @click="handleJoinRoom" :disabled="!roomCode || loading">
            {{ loading ? 'Joining...' : 'Join Room' }}
          </button>
        </div>
      </div>
      
      <div v-if="error" class="error">{{ error }}</div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { useGameStore } from '../stores/game'

export default {
  name: 'Home',
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()
    const gameStore = useGameStore()
    
    const roomCode = ref('')
    const error = ref('')
    const loading = ref(false)
    const availableGames = ref([])
    const selectedGame = ref('number_picker')
    
    const username = computed(() => authStore.getUsername)
    
    // Fetch available games on component mount
    const fetchAvailableGames = async () => {
      try {
        const response = await axios.get('/api/games')
        availableGames.value = response.data
        if (availableGames.value.length > 0) {
          selectedGame.value = availableGames.value[0].name
        }
      } catch (err) {
        console.error('Failed to fetch games:', err)
        // Fallback to default game
        availableGames.value = [
          { name: 'number_picker', display_name: 'Number Picker' }
        ]
      }
    }
    
    const handleLogout = () => {
      authStore.logout()
      router.push('/login')
    }
    
    const handleCreateRoom = async () => {
      error.value = ''
      loading.value = true
      
      const result = await gameStore.createRoom(selectedGame.value)
      
      loading.value = false
      
      if (result.success) {
        router.push(`/room/${result.roomCode}`)
      } else {
        error.value = result.error
      }
    }
    
    const handleJoinRoom = async () => {
      error.value = ''
      loading.value = true
      
      const result = await gameStore.joinRoom(roomCode.value)
      
      loading.value = false
      
      if (result.success) {
        router.push(`/room/${roomCode.value}`)
      } else {
        error.value = result.error
      }
    }
    
    // Fetch games on mount
    fetchAvailableGames()
    
    return {
      username,
      roomCode,
      error,
      loading,
      availableGames,
      selectedGame,
      handleLogout,
      handleCreateRoom,
      handleJoinRoom
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
  margin-bottom: 40px;
}

h1 {
  color: #333;
  margin: 0;
}

.logout-btn {
  background: #e74c3c;
  color: white;
}

.logout-btn:hover {
  background: #c0392b;
}

.actions {
  display: flex;
  gap: 30px;
  align-items: center;
  margin-top: 30px;
}

.action-card {
  flex: 1;
  padding: 20px;
  border: 2px solid #eee;
  border-radius: 10px;
  min-height: 250px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.action-card h2 {
  color: #667eea;
  margin-bottom: 10px;
}

.action-card p {
  color: #666;
  margin-bottom: 20px;
}

.game-selection {
  margin-bottom: 20px;
}

.game-selection label {
  display: block;
  color: #333;
  font-weight: 600;
  margin-bottom: 8px;
}

.game-select {
  width: 100%;
  padding: 10px;
  border: 2px solid #ddd;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
  transition: border-color 0.3s ease;
}

.game-select:hover {
  border-color: #667eea;
}

.game-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 5px rgba(102, 126, 234, 0.3);
}

.action-card input {
  margin-bottom: 15px;
  text-align: center;
  text-transform: uppercase;
  font-weight: bold;
  letter-spacing: 2px;
}

.action-card button {
  background: #667eea;
  color: white;
  width: 100%;
}

.action-card button:hover:not(:disabled) {
  background: #5568d3;
}

.divider {
  font-weight: bold;
  color: #999;
  font-size: 20px;
}

@media (max-width: 768px) {
  .actions {
    flex-direction: column;
  }
  
  .divider {
    transform: rotate(90deg);
  }
}
</style>
