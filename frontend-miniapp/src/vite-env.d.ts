/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** URL standalone-сайта (например, https://services.example.com).
   *  Используется mini-app внутри MAX для редиректа обратно при start_param=student_login.
   *  Если пусто — редирект отключён и mini-app работает только внутри MAX. */
  readonly VITE_WEBAPP_URL?: string;
  readonly VITE_SITE_URL?: string;
  /** Username бота MAX — для deeplink-логина из standalone-сайта. */
  readonly VITE_MAX_BOT_USERNAME?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
