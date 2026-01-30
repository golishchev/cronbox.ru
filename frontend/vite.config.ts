import { defineConfig, type PluginOption } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { sentryVitePlugin } from '@sentry/vite-plugin'
import packageJson from './package.json'

export default defineConfig(({ mode }) => {
  const plugins: PluginOption[] = [react()]

  // Upload source maps to Sentry on production builds
  if (mode === 'production' && process.env.VITE_SENTRY_DSN) {
    plugins.push(
      sentryVitePlugin({
        org: process.env.SENTRY_ORG,
        project: process.env.SENTRY_PROJECT,
        authToken: process.env.SENTRY_AUTH_TOKEN,
        telemetry: false,
        sourcemaps: {
          assets: './dist/**',
        },
      })
    )
  }

  return {
    plugins,
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    define: {
      __APP_VERSION__: JSON.stringify(packageJson.version),
    },
    build: {
      // Generate source maps for production
      sourcemap: true,
    },
    server: {
      port: 3000,
      proxy: {
        '/v1': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
        '/uploads': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
