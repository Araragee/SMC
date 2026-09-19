// Washi. Built once into an offscreen canvas and reused for every frame —
// the paper never moves, the camera moves behind it.

import { mulberry32, fbm1 } from './rng.js'

let cached = null

export function getPaper(env, W, H) {
  if (cached && cached.w === W && cached.h === H) return cached.canvas
  const canvas = env.createCanvas(W, H)
  const ctx = canvas.getContext('2d')
  const rnd = mulberry32(20240516)

  // base tone — warm, slightly uneven
  const base = ctx.createLinearGradient(0, 0, W * 0.3, H)
  base.addColorStop(0, '#f6f0e2')
  base.addColorStop(0.5, '#f1ead9')
  base.addColorStop(1, '#eae2cd')
  ctx.fillStyle = base
  ctx.fillRect(0, 0, W, H)

  // slow stains, as if the sheet had been rolled up for years
  for (let i = 0; i < 26; i++) {
    const x = rnd() * W
    const y = rnd() * H
    const r = (0.08 + rnd() * 0.28) * W
    const g = ctx.createRadialGradient(x, y, 0, x, y, r)
    const warm = rnd() > 0.45
    g.addColorStop(0, warm ? 'rgba(206,186,148,0.16)' : 'rgba(255,252,243,0.2)')
    g.addColorStop(1, 'rgba(0,0,0,0)')
    ctx.fillStyle = g
    ctx.fillRect(x - r, y - r, r * 2, r * 2)
  }

  // kozo fibres
  ctx.lineCap = 'round'
  for (let i = 0; i < 900; i++) {
    const x = rnd() * W
    const y = rnd() * H
    const len = 8 + rnd() * 70
    const a = rnd() * Math.PI
    ctx.globalAlpha = 0.03 + rnd() * 0.07
    ctx.strokeStyle = rnd() > 0.5 ? '#ffffff' : '#c3b596'
    ctx.lineWidth = 0.6 + rnd() * 1.5
    ctx.beginPath()
    ctx.moveTo(x, y)
    for (let s = 1; s <= 4; s++) {
      const t = s / 4
      ctx.lineTo(
        x + Math.cos(a) * len * t + (fbm1(t * 5 + i, i, 2) - 0.5) * 7,
        y + Math.sin(a) * len * t + (fbm1(t * 5 + i + 77, i + 3, 2) - 0.5) * 7,
      )
    }
    ctx.stroke()
  }
  ctx.globalAlpha = 1

  // fine tooth
  const img = ctx.getImageData(0, 0, W, H)
  const d = img.data
  for (let i = 0; i < d.length; i += 4) {
    const n = (rnd() - 0.5) * 13
    d[i] = Math.max(0, Math.min(255, d[i] + n))
    d[i + 1] = Math.max(0, Math.min(255, d[i + 1] + n))
    d[i + 2] = Math.max(0, Math.min(255, d[i + 2] + n * 0.9))
  }
  ctx.putImageData(img, 0, 0)

  // a breath of shadow at the edges so the sheet sits on a table
  const vig = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.35, W / 2, H / 2, Math.max(W, H) * 0.78)
  vig.addColorStop(0, 'rgba(0,0,0,0)')
  vig.addColorStop(1, 'rgba(88,72,44,0.2)')
  ctx.fillStyle = vig
  ctx.fillRect(0, 0, W, H)

  cached = { canvas, w: W, h: H }
  return canvas
}
