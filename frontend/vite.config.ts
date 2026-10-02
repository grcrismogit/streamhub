import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false, // no exponer el código fuente en producción
    chunkSizeWarningLimit: 600,
  },
  server: { port: 5173 },
})
