// Resolution order matters. A value baked in at build time wins, because a
// host that builds the bundle itself (Render's static site) has no way to
// generate /env-config.js at runtime — it would otherwise serve the committed
// public/env-config.js, which hardcodes localhost:8000, and every API call
// from the deployed site would hit the visitor's own machine.
//
// window._env_ remains the fallback for the Docker image, which is built once
// with no VITE_API_BASE_URL and has entrypoint.sh write the file per container.
export const API_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (window as any)._env_?.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin);
export const NUDGE_COOLDOWN_MS = 60 * 60 * 1000; // 1 hour
export const PAGE_SIZE = 5;
