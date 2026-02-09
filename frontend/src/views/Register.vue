<template>
  <div class="container">
    <div class="card">
      <h1>Register</h1>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <input
            v-model="username"
            type="text"
            placeholder="Username"
            required
          />
        </div>
        <div class="form-group">
          <input
            v-model="password"
            type="password"
            placeholder="Password"
            required
            minlength="6"
          />
        </div>
        <div class="form-group">
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="Confirm Password"
            required
            minlength="6"
          />
        </div>
        <div v-if="error" class="error">{{ error }}</div>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Registering...' : 'Register' }}
        </button>
      </form>
      <p class="link-text">
        Already have an account?
        <router-link to="/login">Login here</router-link>
      </p>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export default {
  name: 'Register',
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()
    
    const username = ref('')
    const password = ref('')
    const confirmPassword = ref('')
    const error = ref('')
    const loading = ref(false)
    
    const handleRegister = async () => {
      error.value = ''
      
      if (password.value !== confirmPassword.value) {
        error.value = 'Passwords do not match'
        return
      }
      
      if (password.value.length < 6) {
        error.value = 'Password must be at least 6 characters'
        return
      }
      
      loading.value = true
      
      const result = await authStore.register(username.value, password.value)
      
      loading.value = false
      
      if (result.success) {
        router.push('/home')
      } else {
        error.value = result.error
      }
    }
    
    return {
      username,
      password,
      confirmPassword,
      error,
      loading,
      handleRegister
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
}

h1 {
  margin-bottom: 30px;
  color: #333;
}

.form-group {
  margin-bottom: 20px;
}

button {
  width: 100%;
  background: #667eea;
  color: white;
  font-weight: bold;
  margin-top: 10px;
}

button:hover:not(:disabled) {
  background: #5568d3;
}

.link-text {
  margin-top: 20px;
  color: #666;
}

.link-text a {
  color: #667eea;
  text-decoration: none;
  font-weight: bold;
}

.link-text a:hover {
  text-decoration: underline;
}
</style>
