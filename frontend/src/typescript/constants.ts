export const API_URL = (window as any)._env_?.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin);
export const NUDGE_COOLDOWN_MS = 60 * 60 * 1000; // 1 hour
export const PAGE_SIZE = 5;
