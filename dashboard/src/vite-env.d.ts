/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the API. Defaults to the `/api` dev-server proxy. */
  readonly VITE_API_URL?: string
  /** 'true' shows the login page until a token is present. */
  readonly VITE_AUTH_REQUIRED?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
