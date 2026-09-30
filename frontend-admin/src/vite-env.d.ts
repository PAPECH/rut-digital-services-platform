/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MAX_BOT_USERNAME: string;
  readonly VITE_ADMIN_CSRF_COOKIE_NAME?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
