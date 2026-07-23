import { useEffect, useState } from 'react'

import { authService } from '@/services/authService'
import { useAuthStore } from '@/store/auth.store'

/**
 * Confirms the persisted `isAuthenticated` flag against the server once on
 * app mount. That flag only reflects "we believe a cookie exists" — it's
 * never confirmed with the server, and since `refresh` is never invoked
 * anywhere, a cookie that silently expired (browser reopened after 60min)
 * would otherwise flash the protected shell before the first real API call
 * 401s and bounces the user. Returns `checkingAuth` so the caller can hold
 * off rendering routes until this resolves.
 */
export function useAuthBootstrap(): boolean {
  const [checkingAuth, setCheckingAuth] = useState(true)
  const setAuth = useAuthStore((s) => s.setAuth)
  const clearAuth = useAuthStore((s) => s.clearAuth)

  useEffect(() => {
    let cancelled = false
    authService
      .me()
      .then((user) => {
        if (!cancelled) setAuth(user)
      })
      .catch(() => {
        if (!cancelled) clearAuth()
      })
      .finally(() => {
        if (!cancelled) setCheckingAuth(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return checkingAuth
}
