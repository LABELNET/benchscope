import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 开发时后端默认 8080（benchscope serve --port 8080）
const BACKEND = process.env.BENCHSCOPE_BACKEND || 'http://127.0.0.1:8080'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/ws': { target: BACKEND, ws: true, changeOrigin: true },
    },
  },
  build: {
    outDir: fileURLToPath(new URL('../benchscope/webui', import.meta.url)),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ['echarts'],
          antd: ['ant-design-vue', '@ant-design/icons-vue'],
          vue: ['vue', 'vue-router', 'pinia', 'axios'],
        },
      },
    },
  },
})
