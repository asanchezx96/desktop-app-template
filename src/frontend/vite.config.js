import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig(({ mode }) => {
  // Cargar variables de entorno desde el directorio principal (donde está .env)
  const env = loadEnv(mode, path.resolve(__dirname, '../../'), '')
  const port = parseInt(env.SERVER_PORT || '15050', 10)

  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    server: {
      host: '0.0.0.0',
      port: 15173,
      proxy: {
        '/api': `http://127.0.0.1:${port}`,
        '/ws': {
          target: `ws://127.0.0.1:${port}`,
          ws: true,
        },
      },
    },
  }
})

