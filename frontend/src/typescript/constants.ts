// A bare hostname gets https://. Render's blueprint wires VITE_API_BASE_URL
// from the API service's `host` property, which resolves to a scheme-less
// `smc-api.onrender.com` — render.yaml has no way to concatenate a scheme on.
// Axios reads a scheme-less base as a relative path, so without this every
// call would go to the static site's own origin and 404.
const withScheme = (url: string): string =>
  /^[a-z][a-z0-9+.-]*:\/\//i.test(url) ? url : `https://${url}`

// Resolution order matters. A value baked in at build time wins, because a
// host that builds the bundle itself (Render's static site) has no way to
// generate /env-config.js at runtime.
//
// window._env_ remains the fallback for the Docker image, which is built once
// with no VITE_API_BASE_URL and has entrypoint.sh write the file per container.
// The committed public/env-config.js leaves the value empty on purpose, so a
// static build with no VITE_API_BASE_URL falls through to the page's own
// origin rather than sending every visitor's API calls to their own machine.
const configuredApiUrl: string =
  import.meta.env.VITE_API_BASE_URL || (window as any)._env_?.VITE_API_BASE_URL || ''

export const API_URL = configuredApiUrl
  ? withScheme(configuredApiUrl.trim().replace(/\/+$/, ''))
  : import.meta.env.DEV
    ? 'http://localhost:8000'
    : window.location.origin
export const NUDGE_COOLDOWN_MS = 60 * 60 * 1000 // 1 hour
export const PAGE_SIZE = 5

// The instrument store is built but not open for business yet. Flipping this
// to true restores the Shop nav entries, the shop routes and the teacher's
// order history — nothing was deleted.
export const SHOP_ENABLED = false
