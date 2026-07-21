import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from '@/store/auth.store'
import AppLayout from '@/components/common/AppLayout'
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
