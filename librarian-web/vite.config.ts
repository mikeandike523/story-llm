import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { fileURLToPath } from 'url'
import path from 'path'
import fs from 'fs'
import { FaCropSimple } from 'react-icons/fa6'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)


const overridePort = process.env.PORT ? parseInt(process.env.PORT, 10) : undefined;
const overridePortPreview = process.env.PREVIEW_PORT ? parseInt(process.env.PREVIEW_PORT, 10): undefined

function getConfigVar(server: "server" | "preview", varName: string){
  return JSON.parse(fs.readFileSync(path.resolve(__dirname, "config", server, varName + ".json" ), {
    encoding: "utf-8"
  }))
}

const backendUrlServer = getConfigVar("server","VITE_BACKEND_URL")
const backendUrlPreview = getConfigVar("server","VITE_BACKEND_URL")

const backendUrl = process.env.NODE_ENV === "production" ? backendUrlPreview : backendUrlServer

console.log(process.env.NODE_ENV)
console.log(process.env.PORT)


// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  
  server: {
    port:  overridePort || getConfigVar("server", "port") || 3000,  
    allowedHosts: getConfigVar("server", "allowedHosts")
  },
  preview:{
    port:  overridePortPreview || getConfigVar("preview", "port") || 3001,
    allowedHosts: getConfigVar("preview", "allowedHosts")
  },
  define: {
    "import.meta.env.VITE_BACKEND_URL":JSON.stringify(backendUrl)
  }
})
