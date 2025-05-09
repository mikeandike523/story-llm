/// <reference types="vite/client" />


interface ImportMetaEnv {
  readonly VITE_BACKEND_URL: string;
  // Add more as needed...
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}