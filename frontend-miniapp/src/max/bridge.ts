interface MaxUser {
  id?: string | number;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
}

interface MaxBackButton {
  show?: () => void;
  hide?: () => void;
  onClick?: (cb: () => void) => void;
  offClick?: (cb: () => void) => void;
}

interface MaxWebApp {
  initData?: string;
  initDataUnsafe?: {
    user?: MaxUser;
    start_param?: string;
  };
  ready?: () => void;
  close?: () => void;
  BackButton?: MaxBackButton;
  requestContact?: () => Promise<{
    phone: string;
    authDate: string;
    hash: string;
  }>;
  downloadFile?: (url: string, name: string) => void;
  openCodeReader?: (cb: (s: string) => void) => void;
  enableClosingConfirmation?: () => void;
  openLink?: (url: string) => void;
  openMaxLink?: (url: string) => void;
}

declare global {
  interface Window {
    WebApp?: MaxWebApp;
  }
}

export function getWebApp(): MaxWebApp | null {
  return window.WebApp ?? null;
}

/**
 * Открыто ли мини-приложение внутри MAX (есть Bridge и подписанный initData),
 * или это standalone-сайт в обычном браузере.
 */
export function isInsideApp(): boolean {
  return Boolean(window.WebApp?.initData);
}

export function getInitData(): string | null {
  const wa = getWebApp();
  if (wa?.initData) return wa.initData;

  // dev fallback: ?initData=... в query
  const params = new URLSearchParams(window.location.search);
  return params.get("initData") || params.get("tgWebAppData") || null;
}

export function getInitUser(): MaxUser | null {
  return getWebApp()?.initDataUnsafe?.user ?? null;
}

export function getStartParam(): string | null {
  const wa = getWebApp();
  if (wa?.initDataUnsafe?.start_param) return wa.initDataUnsafe.start_param;
  return (
    new URLSearchParams(window.location.search).get("WebAppStartParam") || null
  );
}

let currentBackButtonHandler: (() => void) | null = null;

export function setupBackButton(visible: boolean, onClick?: () => void): void {
  const bb = getWebApp()?.BackButton;
  if (!bb) return;
  // Every call installs a fresh closure, so without unsubscribing the previous one first,
  // handlers pile up across navigations (App.tsx calls this on every route change) and a
  // single back-button tap fires all of them at once, jumping back several history entries
  // instead of one.
  if (currentBackButtonHandler) {
    bb.offClick?.(currentBackButtonHandler);
    currentBackButtonHandler = null;
  }
  if (visible) {
    bb.show?.();
    if (onClick) {
      bb.onClick?.(onClick);
      currentBackButtonHandler = onClick;
    }
  } else {
    bb.hide?.();
  }
}

export function ready(): void {
  getWebApp()?.ready?.();
}

export function requestContact(): Promise<{
  phone: string;
  authDate: string;
  hash: string;
}> {
  const wa = getWebApp();
  if (!wa?.requestContact) {
    return Promise.reject(
      new Error("requestContact недоступен в этом клиенте"),
    );
  }
  return (
    wa.requestContact as () => Promise<{
      phone: string;
      authDate: string;
      hash: string;
    }>
  )();
}

export function openMaxLink(url: string): void {
  const wa = getWebApp();
  if (wa?.openMaxLink) wa.openMaxLink(url);
  else window.open(url, "_blank");
}
export function downloadFile(url: string, name: string): void {
  const wa = getWebApp();
  if (wa?.downloadFile) wa.downloadFile(url, name);
  else window.open(url, "_blank");
}

export function openLink(url: string): void {
  const wa = getWebApp();
  console.log(
    "Opening link",
    url,
    "via",
    wa?.openLink ? "WebApp.openLink" : "window.open",
  );
  // if (wa?.openLink) wa.openLink(url);
  // else window.open(url, "_blank");
  window.open(url, "_blank");
}
export function enableClosingConfirmation(): void {
  getWebApp()?.enableClosingConfirmation?.();
}
