import axios, { type AxiosError } from 'axios'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/auth.store'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
  // Send the httpOnly auth cookies with every request. No Authorization
  // header / localStorage token handling — the browser attaches the cookies
  // automatically and JS never touches the tokens.
  withCredentials: true,
})

// Handle 401 and surface error toasts
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ error: string }>) => {
    const status  = error.response?.status
    const message = error.response?.data?.error

    if (status === 401) {
      // Must clear the persisted `isAuthenticated` flag too, not just the raw
      // localStorage tokens — otherwise GuestRoute still thinks we're logged in
      // and immediately bounces /login back to /dashboard, causing a reload loop.
      const wasAuthenticated = useAuthStore.getState().isAuthenticated
      useAuthStore.getState().clearAuth()
      if (wasAuthenticated && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    if (!axios.isCancel(error) && status !== 422) {
      toast.error(message || 'Something went wrong.')
    }

    return Promise.reject(error)
  }
)
