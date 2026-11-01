import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/datasets': 'http://127.0.0.1:8000',
      '/observations': 'http://127.0.0.1:8000',
      '/comparison': 'http://127.0.0.1:8000',
      '/diagnostics': 'http://127.0.0.1:8000',
      '/ai': 'http://127.0.0.1:8000',
      '/visualization': 'http://127.0.0.1:8000'
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
});
