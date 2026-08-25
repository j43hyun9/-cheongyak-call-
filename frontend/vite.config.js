import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    allowedHosts: true,   // ngrok 등 외부 도메인 접속 허용
    proxy: {
      '/chat':      { target: 'http://localhost:8000', changeOrigin: true },
      '/stt':       { target: 'http://localhost:8000', changeOrigin: true },
      '/tts':       { target: 'http://localhost:8000', changeOrigin: true },
      '/ipo':       { target: 'http://localhost:8000', changeOrigin: true },
      '/schedules':        { target: 'http://localhost:8000', changeOrigin: true },
      '/sadtalker_output': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
