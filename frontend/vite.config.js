import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat':      { target: 'http://localhost:8000', changeOrigin: true },
      '/ipo':       { target: 'http://localhost:8000', changeOrigin: true },
      '/schedules': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
