import { BrowserRouter } from 'react-router-dom'

import Spinner from '@/components/ui/Spinner'
import { useAuthBootstrap } from '@/hooks/useAuthBootstrap'
import AppRoutes from '@/routes/AppRoutes'

export default function App() {
  const checkingAuth = useAuthBootstrap()

  if (checkingAuth) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface">
        <Spinner size={28} />
      </div>
    )
  }

  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
