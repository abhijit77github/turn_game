import { defineStore } from 'pinia'
import axios from 'axios'

const API_URL = '/api'

export const useGameStore = defineStore('game', {
  state: () => ({
    roomCode: null,
    gameType: 'number_picker',
    players: [],
    creator: null,
    gameStarted: false,
    currentPlayer: null,
    choices: [],
    turn: 0,
    round: 0,
    maxTurns: 5,
    turnTime: 10,
    winner: null,
    gameEnded: false,
    ws: null,
    connectionStatus: 'disconnected',
    canRestart: false,
    // Chain Reaction specific
    board: [],
    playerColors: {},
    explosions: [],
    queuedEvents: [],
    processingEvents: false,
    lastMoveTime: 0,
    moveInProgress: false,
    currentExplosionIndex: 0
  }),
  
  getters: {
    isCreator: (state) => {
      const username = localStorage.getItem('username')
      return state.creator === username
    },
    isMyTurn: (state) => {
      const username = localStorage.getItem('username')
      return state.currentPlayer === username
    }
  },
  
  actions: {
    async createRoom(gameType = 'number_picker') {
      try {
        const response = await axios.post(`${API_URL}/room/create`, {
          game_type: gameType
        })
        this.roomCode = response.data.room_code
        this.creator = response.data.creator
        return { success: true, roomCode: this.roomCode }
      } catch (error) {
        return {
          success: false,
          error: error.response?.data?.detail || 'Failed to create room'
        }
      }
    },
    
    async joinRoom(roomCode) {
      try {
        const response = await axios.post(`${API_URL}/room/join`, {
          room_code: roomCode
        })
        
        this.roomCode = roomCode
        this.players = response.data.players
        this.creator = response.data.creator
        
        return { success: true }
      } catch (error) {
        return {
          success: false,
          error: error.response?.data?.detail || 'Failed to join room'
        }
      }
    },
    
    connectWebSocket(roomCode, username) {
      if (this.ws) {
        this.ws.close()
      }
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/${roomCode}/${username}`
      
      this.ws = new WebSocket(wsUrl)
      this.connectionStatus = 'connecting'
      
      this.ws.onopen = () => {
        this.connectionStatus = 'connected'
      }
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.handleWebSocketMessage(data)
      }
      
      this.ws.onerror = () => {
        this.connectionStatus = 'error'
      }
      
      this.ws.onclose = (event) => {
        this.connectionStatus = 'disconnected'
        
        // Only attempt reconnection if not a normal closure and room still exists
        // Code 1000 is normal closure, 1001 is going away
        if (this.roomCode && event.code !== 1000 && event.code !== 1001) {
          setTimeout(() => {
            if (this.roomCode) {
              this.connectWebSocket(this.roomCode, username)
            }
          }, 3000)
        }
      }
    },
    
    handleWebSocketMessage(data) {
      switch (data.type) {
        case 'room_state':
          this.players = data.room.players
          this.creator = data.room.creator
          this.gameStarted = data.room.game_started
          this.gameType = data.room.game_type || 'number_picker'
          
          // Handle reconnection to ended game
          if (data.game_ended) {
            this.gameEnded = true
            this.winner = data.game_ended.winner
            this.canRestart = data.game_ended.can_restart
          }
          break
          
        case 'player_joined':
          this.players = data.players
          break
          
        case 'player_left':
          this.players = data.players
          this.creator = data.creator
          break
          
        case 'game_started':
          console.log('Game started, data:', data)
          this.gameStarted = true
          this.gameEnded = false
          this.currentPlayer = data.current_player
          this.choices = data.choices || []
          this.turn = data.turn
          this.round = data.round || 0
          this.maxTurns = data.max_turns
          this.turnTime = data.turn_time
          
          // Chain Reaction specific data
          if (data.board) {
            this.board = data.board
            this.playerColors = data.player_colors || {}
            this.explosions = data.explosions || []
          }
          
          console.log('Set choices to:', this.choices)
          console.log('Set turn to:', this.turn)
          this.winner = null
          break
          
        case 'next_turn':
          console.log('Next turn, data:', data)
          this.currentPlayer = data.current_player
          this.choices = data.choices || []
          this.turn = data.turn
          this.round = data.round || 0
          
          // Chain Reaction specific data
          if (data.board) {
            this.board = data.board
            this.explosions = data.explosions || []
          }
          
          // Reset move locks when new turn starts
          this.moveInProgress = false
          this.processingEvents = false
          this.queuedEvents = []
          this.currentExplosionIndex = 0
          
          console.log('Set choices to:', this.choices)
          break
          
        case 'game_events':
          // Handle batched events with timing
          this.queuedEvents = data.events || []
          
          // Update board immediately if provided
          if (data.board) {
            this.board = data.board
          }
          
          if (this.queuedEvents.length > 0) {
            this.processNextEvent()
          } else {
            // No events to process, reset immediately
            this.moveInProgress = false
          }
          break
          
        case 'add_ball':
          console.log('Ball added:', data)
          if (data.board) {
            this.board = data.board
          }
          this.explosions = []
          break
          
        case 'explosion':
          console.log('Explosion event:', data)
          this.explosions = [{
            x: data.x,
            y: data.y,
            color: data.color,
            type: 'explosion'
          }]
          break
          
        case 'spread':
          console.log('Spread event:', data)
          this.explosions = [{
            from_x: data.from_x,
            from_y: data.from_y,
            to_x: data.to_x,
            to_y: data.to_y,
            color: data.color,
            type: 'spread'
          }]
          break
          
        case 'game_over':
          console.log('Game over:', data)
          this.gameEnded = true
          this.winner = data.winner
          this.explosions = []
          break
          
        case 'auto_choice':
          // Player's turn was auto-completed
          break
          
        case 'game_ended':
          this.gameEnded = true
          this.gameStarted = false
          this.winner = data.winner
          this.canRestart = data.can_restart
          
          // Update board and colors for final state display
          if (data.board) {
            this.board = data.board
          }
          if (data.player_colors) {
            this.playerColors = data.player_colors
          }
          
          // Clear any ongoing animations
          this.explosions = []
          this.queuedEvents = []
          this.processingEvents = false
          break
          
        case 'error':
          console.error('WebSocket error:', data.message)
          // Unlock moves on error to allow retry
          this.moveInProgress = false
          this.processingEvents = false
          this.queuedEvents = []
          break
      }
    },
    
    processNextEvent() {
      if (this.processingEvents || this.queuedEvents.length === 0) {
        return
      }
      
      this.processingEvents = true
      const event = this.queuedEvents.shift()
      const currentTimeMs = Date.now()
      
      // Update board state if event contains it
      if (event.board) {
        this.board = event.board
      }
      
      // Use requestAnimationFrame for smoother state updates
      requestAnimationFrame(() => {
        // Show explosion state for animation - only ONE at a time
        if (event.type === 'explosion') {
          this.explosions = [{
            x: event.x,
            y: event.y,
            color: event.color,
            type: 'explosion'
          }]
          
          // Clear explosion after animation completes (2 seconds for visual clarity)
          setTimeout(() => {
            if (this.explosions.length > 0 && this.explosions[0].type === 'explosion') {
              this.explosions = []
            }
          }, 2000)
        } else if (event.type === 'spread') {
          this.explosions = [{
            from_x: event.from_x,
            from_y: event.from_y,
            to_x: event.to_x,
            to_y: event.to_y,
            color: event.color,
            type: 'spread'
          }]
          
          // Clear spread after flying ball animation (1.5 seconds)
          setTimeout(() => {
            if (this.explosions.length > 0 && this.explosions[0].type === 'spread') {
              this.explosions = []
            }
          }, 1500)
        } else if (event.type === 'add_ball') {
          this.explosions = []
        }
      })
      
      // Schedule next event based on timing metadata
      const nextEvent = this.queuedEvents[0]
      if (nextEvent) {
        const currentTime = event.time || 0
        const nextTime = nextEvent.time || 0
        // Use the time delta from the event metadata, minimum 200ms
        const delay = Math.max(200, (nextTime - currentTime) * 1000)
        
        setTimeout(() => {
          this.processingEvents = false
          this.processNextEvent()
        }, delay)
      } else {
        // All events processed
        this.processingEvents = false
        this.explosions = []
        console.log('All events processed, UI ready for next turn')
      }
    },
    
    startGame() {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        console.log('Sending start_game message')
        this.ws.send(JSON.stringify({ type: 'start_game' }))
      } else {
        console.error('WebSocket not ready', this.ws?.readyState)
      }
    },
    
    makeChoice(choice) {
      // Prevent rapid successive moves
      const now = Date.now()
      if (this.moveInProgress || now - this.lastMoveTime < 300) {
        console.log('Move blocked:', { moveInProgress: this.moveInProgress, timeSinceLastMove: now - this.lastMoveTime })
        return
      }
      
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.moveInProgress = true
        this.lastMoveTime = now
        console.log('Sending move:', choice)
        this.ws.send(JSON.stringify({
          type: 'make_choice',
          action: choice
        }))
      }
    },
    
    exitGame() {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'exit_game' }))
      }
      
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      
      this.resetState()
    },
    
    restartGame() {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'restart_game' }))
      }
    },
    
    resetState() {
      this.roomCode = null
      this.players = []
      this.creator = null
      this.gameStarted = false
      this.currentPlayer = null
      this.choices = []
      this.turn = 0
      this.winner = null
      this.gameEnded = false
      this.canRestart = false
    }
  }
})
