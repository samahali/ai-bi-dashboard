import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { User } from '@/types'

// Tokens are NOT stored here or in localStorage — they live in httpOnly
// cookies set by the backend, unreadable by JavaScript (see docs/SECURITY.md).
// This store only tracks the current user and an authenticated flag for
// routing. `isAuthenticated` reflects "we believe a valid session cookie
// exists"; the server is the source of truth and a 401 clears it.
interface AuthState {
  user: User | null
  isAuthenticated: boolean

  setAuth: (user: User) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      setAuth: (user) => set({ user, isAuthenticated: true }),

      clearAuth: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: 'bi-auth',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
)
