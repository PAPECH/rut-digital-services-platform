/**
 * Web Push уведомления.
 */

const PREF_KEY = "mfc.admin.push";

export function isNotifySupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function isNotifyEnabled(): boolean {
  if (!isNotifySupported()) return false;
  if (localStorage.getItem(PREF_KEY) !== "1") return false;
  return Notification.permission === "granted";
}

export async function requestNotifyPermission(): Promise<boolean> {
  if (!isNotifySupported()) return false;
  if (Notification.permission === "granted") {
    localStorage.setItem(PREF_KEY, "1");
    return true;
  }
  const res = await Notification.requestPermission();
  if (res === "granted") {
    localStorage.setItem(PREF_KEY, "1");
    return true;
  }
  return false;
}

export function disableNotify(): void {
  localStorage.setItem(PREF_KEY, "0");
}

export function notify(title: string, body?: string): void {
  if (!isNotifyEnabled()) return;
  try {
    const n = new Notification(title, {
      body,
      tag: "mfc-ticket",
      renotify: true,
    } as NotificationOptions);
    // Самозакрытие через 6с
    setTimeout(() => n.close(), 6000);
  } catch {
    /* ignore */
  }
  playBeep();
}

let audioCtx: AudioContext | null = null;

function getAudio(): AudioContext | null {
  if (typeof window === "undefined") return null;
  try {
    if (!audioCtx) {
      const Ctx = (window.AudioContext ||
        (window as any).webkitAudioContext) as typeof AudioContext;
      audioCtx = new Ctx();
    }
    return audioCtx;
  } catch {
    return null;
  }
}

export function playBeep(): void {
  const ctx = getAudio();
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.frequency.value = 880;
  gain.gain.setValueAtTime(0.0001, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.15, ctx.currentTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.25);
  osc.start(ctx.currentTime);
  osc.stop(ctx.currentTime + 0.27);
}
