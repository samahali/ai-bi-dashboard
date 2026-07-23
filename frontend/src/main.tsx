import React, { Suspense, lazy } from 'react'

import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'

import App from './App'
import './index.css'

// Lazy + dev-only: keeps the devtools bundle out of the production build
// entirely (import() is never even called when import.meta.env.PROD).
const ReactQueryDevtools = import.meta.env.PROD
  ? () => null
  : lazy(() =>
      import('@tanstack/react-query-devtools').then((m) => ({
        default: m.ReactQueryDevtools,
      }))
    )

// Read-path error feedback comes from the axios response interceptor in
// services/api.ts, which already toasts the backend's error message for any
// failed request (queries and mutations alike) — a separate QueryCache-level
// handler here would show a second, duplicate toast for the same failure.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 60, // 1 minute
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            fontSize: '14px',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
          },
        }}
      />
      <Suspense fallback={null}>
        <ReactQueryDevtools initialIsOpen={false} />
      </Suspense>
    </QueryClientProvider>
  </React.StrictMode>
)
