import { defineStore } from 'pinia'
import axios from 'axios'

const API_URL = '/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    username: localStorage.getItem('username') || null
  }),
  
  getters: {
    isAuthenticated: (state) => !!state.token,
    getUsername: (state) => state.username
  },
  
  actions: {
    async register(username, password) {
      try {
        const response = await axios.post(`${API_URL}/register`, {
          username,
          password
        })
        
        this.token = response.data.access_token
        this.username = username
        localStorage.setItem('token', this.token)
        localStorage.setItem('username', username)
        
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        
        return { success: true }
      } catch (error) {
        return {
          success: false,
          error: error.response?.data?.detail || 'Registration failed'
        }
      }
    },
    
    async login(username, password) {
      try {
        const response = await axios.post(`${API_URL}/login`, {
          username,
          password
        })
        
        this.token = response.data.access_token
        this.username = username
        localStorage.setItem('token', this.token)
        localStorage.setItem('username', username)
        
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        
        return { success: true }
      } catch (error) {
        return {
          success: false,
          error: error.response?.data?.detail || 'Login failed'
        }
      }
    },
    
    logout() {
      this.token = null
      this.username = null
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      delete axios.defaults.headers.common['Authorization']
    },
    
    initializeAuth() {
      if (this.token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
      }
    }
  }
})
