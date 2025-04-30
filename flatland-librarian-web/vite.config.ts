import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  base: '/flatland-librarian',
  plugins: [react()],
  preview:{
    port: 3001,
    allowedHosts: [
      "localhost",
      "127.0.0.1",
      "aisecure.cmihandbook.com",
    ]
  }
})
