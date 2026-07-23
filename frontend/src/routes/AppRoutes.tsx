import { lazy, Suspense } from 'react'

import { Navigate, Route, Routes } from 'react-router-dom'

import Spinner from '@/components/ui/Spinner'
import AppLayout from '@/layouts/AppLayout'
import { useAuthStore } from '@/store/auth.store'

// Lazy-loaded so each route's page code ships in its own chunk, fetched only
// when the user navigates there, instead of all 9 pages bundled upfront.
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'))
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'))
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'))
const DatasetsPage = lazy(() => import('@/pages/datasets/DatasetsPage'))
const DatasetDetailPage = lazy(() => import('@/pages/datasets/DatasetDetailPage'))
const UploadPage = lazy(() => import('@/pages/datasets/UploadPage'))
const QueryPage = lazy(() => import('@/pages/query/QueryPage'))
const ReportsPage = lazy(() => import('@/pages/reports/ReportsPage'))
const InsightsPage = lazy(() => import('@/pages/insights/InsightsPage'))

function PageFallback() {
  return (
    <div className="flex h-64 items-center justify-center">
      <Spinner size={24} />
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <>{children}</>
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
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
    </Suspense>
  )
}
