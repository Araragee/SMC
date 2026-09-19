// Deterministic randomness. Every frame of the film is a pure function of
// time, so nothing here may depend on call order across frames — each stroke
// seeds its own generator and re-derives the same bristles every time.

export function mulberry32(seed) {
  let a = seed >>> 0
  return function rand() {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function hash(seed, i) {
  let t = (Math.imul(seed ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(i + 1, 0xc2b2ae35)) >>> 0
  t = Math.imul(t ^ (t >>> 13), 0x27d4eb2f) >>> 0
  return ((t ^ (t >>> 16)) >>> 0) / 4294967296
}

// Smooth 1D value noise — the backbone of bristle wobble and dry-brush gaps.
export function noise1(x, seed = 1) {
  const i = Math.floor(x)
  const f = x - i
  const u = f * f * (3 - 2 * f)
  const a = hash(seed, i)
  const b = hash(seed, i + 1)
  return a + (b - a) * u
}

export function fbm1(x, seed = 1, octaves = 3) {
  let sum = 0
  let amp = 0.5
  let freq = 1
  for (let o = 0; o < octaves; o++) {
    sum += amp * noise1(x * freq, seed + o * 101)
    freq *= 2.07
    amp *= 0.5
  }
  return sum / 0.875
}

export const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v)
export const lerp = (a, b, t) => a + (b - a) * t
export const smoothstep = (t) => {
  const x = clamp(t, 0, 1)
  return x * x * (3 - 2 * x)
}
export const easeInOut = (t) => {
  const x = clamp(t, 0, 1)
  return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2
}
export const easeOut = (t) => 1 - Math.pow(1 - clamp(t, 0, 1), 3)
export const easeIn = (t) => Math.pow(clamp(t, 0, 1), 3)
