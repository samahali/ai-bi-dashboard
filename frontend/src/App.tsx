import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from '@/store/auth.store'
import { authService } from '@/services/authService'
import AppLayout from '@/components/common/AppLayout'
import Spinner from '@/components/ui/Spinner'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import DatasetsPage from '@/pages/datasets/DatasetsPage'
import DatasetDetailPage from '@/pages/datasets/DatasetDetailPage'
import UploadPage from '@/pages/datasets/UploadPage'
import QueryPage from '@/pages/query/QueryPage'
import ReportsPage from '@/pages/reports/ReportsPage'
import InsightsPage from '@/pages/insights/InsightsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <>{children}</>
}

export default function App() {
  const [checkingAuth, setCheckingAuth] = useState(true)
  const setAuth = useAuthStore((s) => s.setAuth)
  const clearAuth = useAuthStore((s) => s.clearAuth)

  // The persisted `isAuthenticated` flag only reflects "we believe a cookie
  // exists" — it's never confirmed with the server. Since `refresh` is never
  // invoked anywhere, a cookie that silently expired (browser reopened after
  // 60min) would otherwise flash the protected shell before the first real
  // API call 401s and bounces the user. Confirm once on app mount instead.
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

  if (checkingAuth) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface">
        <Spinner size={28} />
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Guest routes */}
        <Route path="/login"    element={<GuestRoute><LoginPage /></GuestRoute>} />
        <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />

        {/* Protected routes — wrapped in shared layout */}
        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard"          element={<DashboardPage />} />
          <Route path="/datasets"           element={<DatasetsPage />} />
          <Route path="/datasets/upload"    element={<UploadPage />} />
          <Route path="/datasets/:id"       element={<DatasetDetailPage />} />
          <Route path="/query/:datasetId"   element={<QueryPage />} />
          <Route path="/reports"            element={<ReportsPage />} />
          <Route path="/insights/:datasetId" element={<InsightsPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
