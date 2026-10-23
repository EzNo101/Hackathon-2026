/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Základní URL API včetně prefixu, např. http://localhost:8000/api/v1 */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
