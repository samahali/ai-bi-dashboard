import React, { Suspense, lazy } from 'react'
import ReactDOM from 'react-dom/client'
import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import toast, { Toaster } from 'react-hot-toast'
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 60, // 1 minute
    },
  },
  // Centralized read-path error feedback: a failed useQuery previously left
  // `data` undefined with no UI signal at all. One shared handler covers
  // every query without threading an onError into each call site. Toasts
  // are keyed by query key so a polling/refetch loop retrying the same
  // failing query doesn't spam duplicate toasts on every interval.
  queryCache: new QueryCache({
    onError: (_error, query) => {
      toast.error('Failed to load data. Please try again.', {
        id: JSON.stringify(query.queryKey),
      })
    },
  }),
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
