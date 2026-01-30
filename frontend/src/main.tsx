import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as Sentry from '@sentry/react'
import App from './App'
import './lib/i18n' // Initialize i18n
import './index.css'

// Get version from package.json
const APP_VERSION = __APP_VERSION__

// Initialize Sentry for error tracking and performance monitoring
if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE, // development, production
    release: `cronbox-frontend@${APP_VERSION}`,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    // Performance monitoring - capture 10% of transactions
    tracesSampleRate: 0.1,
    // Session replay - capture 10% of sessions, 100% of error sessions
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    // Filter out known non-critical errors
    ignoreErrors: [
      // Network errors
      'Network request failed',
      'Failed to fetch',
      'NetworkError',
      // Browser extensions
      'ResizeObserver loop limit exceeded',
      'Non-Error promise rejection captured',
    ],
  })
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Sentry.ErrorBoundary
      fallback={({ error }) => (
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <h1>Oops! Something went wrong</h1>
          <p>We've been notified and are working on a fix.</p>
          <details style={{ marginTop: '1rem', textAlign: 'left', maxWidth: '600px', margin: '1rem auto' }}>
            <summary>Error details</summary>
            <pre style={{ overflow: 'auto', padding: '1rem', background: '#f5f5f5' }}>
              {error?.toString()}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}
          >
            Reload page
          </button>
        </div>
      )}
    >
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </Sentry.ErrorBoundary>
  </StrictMode>,
)
