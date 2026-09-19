// The ink. Everything you see in the film is drawn by these routines:
// bristle-split strokes with dry-brush streaks, wet bleed, pooling at the
// point where the brush rested, soft washes, mist and far hills.
//
// The rendering is stateless and deterministic: a stroke drawn at progress p
// always looks the same, so the film can be scrubbed, paused or rewound.

import { mulberry32, noise1, fbm1, clamp, lerp } from './rng.js'

export const INK = '#16161a'
export const INK_SOFT = '#3a3a42'

// ---------------------------------------------------------------------------
// path geometry
// ---------------------------------------------------------------------------

// Catmull-Rom through the control points, resampled at roughly even spacing.
function catmullRom(pts, samplesPerSeg) {
  if (pts.length < 2) return pts.map((p) => ({ x: p[0], y: p[1] }))
  const ext = [pts[0], ...pts, pts[pts.length - 1]]
  const out = []
  for (let i = 1; i < ext.length - 2; i++) {
    const [p0, p1, p2, p3] = [ext[i - 1], ext[i], ext[i + 1], ext[i + 2]]
    const n = samplesPerSeg
    for (let s = 0; s < n; s++) {
      const t = s / n
      const t2 = t * t
      const t3 = t2 * t
      out.push({
        x:
          0.5 *
          (2 * p1[0] +
            (-p0[0] + p2[0]) * t +
            (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
            (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
        y:
          0.5 *
          (2 * p1[1] +
            (-p0[1] + p2[1]) * t +
            (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
            (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
      })
    }
  }
  out.push({ x: pts[pts.length - 1][0], y: pts[pts.length - 1][1] })
  return out
}

// Arc-length parameterisation plus per-point normals. Cached on the stroke.
export function buildPath(stroke) {
  if (stroke._path) return stroke._path
  const dense = catmullRom(stroke.pts, 14)
  // even-length resample
  let total = 0
  const segLen = [0]
  for (let i = 1; i < dense.length; i++) {
    total += Math.hypot(dense[i].x - dense[i - 1].x, dense[i].y - dense[i - 1].y)
    segLen.push(total)
  }
  const n = clamp(Math.round(total / 7), 14, 190)
  const pts = []
  let j = 1
  for (let i = 0; i <= n; i++) {
    const target = (i / n) * total
    while (j < segLen.length - 1 && segLen[j] < target) j++
    const t0 = segLen[j - 1]
    const t1 = segLen[j]
    const f = t1 > t0 ? (target - t0) / (t1 - t0) : 0
    pts.push({
      x: lerp(dense[j - 1].x, dense[j].x, f),
      y: lerp(dense[j - 1].y, dense[j].y, f),
      s: total > 0 ? target / total : 0,
    })
  }
  for (let i = 0; i < pts.length; i++) {
    const a = pts[Math.max(0, i - 1)]
    const b = pts[Math.min(pts.length - 1, i + 1)]
    const dx = b.x - a.x
    const dy = b.y - a.y
    const l = Math.hypot(dx, dy) || 1
    pts[i].nx = -dy / l
    pts[i].ny = dx / l
  }
  const bb = { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity }
  for (const p of pts) {
    if (p.x < bb.x0) bb.x0 = p.x
    if (p.y < bb.y0) bb.y0 = p.y
    if (p.x > bb.x1) bb.x1 = p.x
    if (p.y > bb.y1) bb.y1 = p.y
  }
  const w = stroke.w || 16
  stroke._path = { pts, length: total, bbox: { x0: bb.x0 - w, y0: bb.y0 - w, x1: bb.x1 + w, y1: bb.y1 + w } }
  return stroke._path
}

// The hairs of the brush: fixed per stroke, so a stroke keeps its character.
function buildBristles(stroke, count) {
  const key = '_bristles' + count
  if (stroke[key]) return stroke[key]
  const rnd = mulberry32((stroke.seed || 7) * 2654435761)
  const out = []
  for (let b = 0; b < count; b++) {
    const u = count === 1 ? 0.5 : b / (count - 1)
    out.push({
      off: (u - 0.5) * 1.72 + (rnd() - 0.5) * 0.18, // across the ferrule
      alpha: 0.5 + rnd() * 0.5,
      wid: 0.1 + rnd() * 0.12,
      dryPhase: rnd() * 40,
      dryFreq: 0.16 + rnd() * 0.24,
      wob: rnd() * 30,
      wob0: (rnd() - 0.5) * 1.6,
    })
  }
  stroke[key] = out
  return out
}

// Pressure along the stroke: tapered ends, a little life in between.
function widthAt(stroke, s, seed) {
  const tin = stroke.taperIn ?? 0.12
  const tout = stroke.taperOut ?? 0.22
  let w = 1
  if (s < tin) w *= Math.pow(s / tin, 0.55)
  if (s > 1 - tout) w *= Math.pow((1 - s) / tout, 0.7)
  const body = stroke.swell ? 1 + stroke.swell * Math.sin(Math.PI * s) : 1
  return w * body * (0.78 + 0.44 * fbm1(s * 3.4 + seed, seed * 13 + 3, 2))
}

/**
 * Draw one ink stroke at paint progress `p` (0 = untouched, 1 = finished).
 * `opts.alpha` scales the whole stroke, `opts.lod` (0..1) thins the bristle
 * count when the camera is pulled back and nobody can tell.
 */
export function drawStroke(ctx, stroke, p, opts = {}) {
  if (p <= 0.0005) return
  const alphaMul = opts.alpha ?? 1
  if (alphaMul <= 0.004) return
  const path = buildPath(stroke)
  const pts = path.pts
  const w = stroke.w || 16
  const color = stroke.color || INK
  const seed = stroke.seed || 7
  const lod = opts.lod ?? 1
  const base = (stroke.alpha ?? 1) * alphaMul

  const cut = clamp(p, 0, 1)
  const last = Math.max(1, Math.floor(cut * (pts.length - 1)))

  // Half-width at every sample, cached — this is the silhouette of the brush.
  if (!stroke._hw) {
    stroke._hw = pts.map((q) => widthAt(stroke, q.s, seed) * w * 0.5)
  }
  const hw = stroke._hw

  const nb = Math.max(3, Math.round((4 + Math.min(10, w * 0.4)) * lod))
  const bristles = buildBristles(stroke, nb)
  const dry = stroke.dry ?? 0.22

  ctx.save()
  ctx.lineJoin = 'round'
  ctx.lineCap = 'round'
  ctx.fillStyle = color

  // --- wet bleed: ink creeping outwards into the fibres -------------------
  const wet = stroke.wet ?? 0.5
  if (wet > 0) {
    ctx.globalAlpha = clamp(0.1 * wet * base, 0, 1)
    ctx.beginPath()
    for (let i = 0; i <= last; i++) {
      const q = pts[i]
      const e = hw[i] * 1.5 + 2.5
      const x = q.x + q.nx * e
      const y = q.y + q.ny * e
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    for (let i = last; i >= 0; i--) {
      const q = pts[i]
      const e = hw[i] * 1.5 + 2.5
      ctx.lineTo(q.x - q.nx * e, q.y - q.ny * e)
    }
    ctx.closePath()
    ctx.fill()
  }

  // --- the hairs: each lays a band of ink, and skips where the paper wins --
  const bandW = 2 / nb
  for (let b = 0; b < nb; b++) {
    const br = bristles[b]
    const o0 = -1 + b * bandW
    const o1 = o0 + bandW * 1.14
    ctx.globalAlpha = clamp((0.34 + 0.4 * br.alpha) * base, 0, 1)
    let run = []
    const flush = () => {
      if (run.length < 2) {
        run = []
        return
      }
      ctx.beginPath()
      for (let k = 0; k < run.length; k++) {
        const i = run[k]
        const q = pts[i]
        const e = o0 * hw[i] + br.wob0
        if (k === 0) ctx.moveTo(q.x + q.nx * e, q.y + q.ny * e)
        else ctx.lineTo(q.x + q.nx * e, q.y + q.ny * e)
      }
      for (let k = run.length - 1; k >= 0; k--) {
        const i = run[k]
        const q = pts[i]
        const e = o1 * hw[i] + br.wob0
        ctx.lineTo(q.x + q.nx * e, q.y + q.ny * e)
      }
      ctx.closePath()
      ctx.fill()
      run = []
    }
    for (let i = 0; i <= last; i++) {
      // dry-brush: streaks open up as the brush runs out of ink
      const tooth = noise1(i * br.dryFreq + br.dryPhase, seed * 7 + 11)
      if (tooth < dry * (0.45 + 0.62 * pts[i].s)) {
        flush()
        continue
      }
      run.push(i)
    }
    flush()
  }

  // --- the loaded core, where the ink is heaviest -------------------------
  ctx.globalAlpha = clamp(0.5 * base, 0, 1)
  ctx.beginPath()
  for (let i = 0; i <= last; i++) {
    const q = pts[i]
    const e = hw[i] * 0.52
    if (i === 0) ctx.moveTo(q.x + q.nx * e, q.y + q.ny * e)
    else ctx.lineTo(q.x + q.nx * e, q.y + q.ny * e)
  }
  for (let i = last; i >= 0; i--) {
    const q = pts[i]
    const e = hw[i] * 0.52
    ctx.lineTo(q.x - q.nx * e, q.y - q.ny * e)
  }
  ctx.closePath()
  ctx.fill()

  // --- ink pooling where the brush slowed or lifted -----------------------
  const pools = stroke.pool ?? [0.16, 0.72]
  ctx.globalAlpha = clamp(0.26 * alphaMul * (stroke.alpha ?? 1), 0, 1)
  ctx.fillStyle = color
  for (let k = 0; k < pools.length; k++) {
    const s = pools[k]
    if (s > cut) continue
    const idx = clamp(Math.round(s * (pts.length - 1)), 0, pts.length - 1)
    const q = pts[idx]
    // a pool is only ever as wide as the stroke that made it
    const r = hw[idx] * (0.55 + 0.35 * noise1(k * 3.1 + seed, seed))
    if (r < 1.5) continue
    ctx.beginPath()
    ctx.ellipse(q.x + q.nx * r * 0.2, q.y + q.ny * r * 0.2, r * 1.2, r * 0.85, k * 1.3 + seed, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.restore()
}

// ---------------------------------------------------------------------------
// washes, mist, hills — the quiet half of a sumi-e page
// ---------------------------------------------------------------------------

export function wash(ctx, x, y, rx, ry, color, alpha, seed = 3, rot = 0) {
  if (alpha <= 0.002) return
  const rnd = mulberry32(seed * 40503)
  ctx.save()
  ctx.translate(x, y)
  ctx.rotate(rot)
  // a wash is never one blob — it is several bleeding into each other
  for (let i = 0; i < 5; i++) {
    const ox = (rnd() - 0.5) * rx * 0.55
    const oy = (rnd() - 0.5) * ry * 0.55
    const r = rx * (0.55 + rnd() * 0.5)
    const ry2 = ry * (0.55 + rnd() * 0.5)
    const g = ctx.createRadialGradient(ox, oy, 0, ox, oy, Math.max(r, ry2))
    g.addColorStop(0, color)
    g.addColorStop(0.55, color)
    g.addColorStop(1, 'rgba(0,0,0,0)')
    ctx.globalAlpha = alpha * (0.32 + rnd() * 0.3)
    ctx.fillStyle = g
    ctx.save()
    ctx.scale(1, ry2 / Math.max(r, 0.001))
    ctx.beginPath()
    ctx.arc(ox, (oy * r) / Math.max(ry2, 0.001), Math.max(r, ry2), 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }
  ctx.restore()
}

// Mist is not a band of white — it is where the paper shows through the ink.
export function mistBand(ctx, x, y, w, h, alpha, drift = 0, seed = 5) {
  if (alpha <= 0.002) return
  const rnd = mulberry32(seed * 7717)
  ctx.save()
  for (let i = 0; i < 5; i++) {
    const rx = w * (0.22 + rnd() * 0.3)
    const ry = h * (0.3 + rnd() * 0.55)
    const ox = x + (rnd() - 0.5) * w * 0.8 + Math.sin(drift * (0.4 + rnd() * 0.5) + i) * w * 0.06
    const oy = y + (rnd() - 0.5) * h * 0.9
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx)
    g.addColorStop(0, 'rgba(249,244,233,0.92)')
    g.addColorStop(0.45, 'rgba(249,244,233,0.6)')
    g.addColorStop(1, 'rgba(249,244,233,0)')
    ctx.save()
    ctx.translate(ox, oy)
    ctx.scale(1, ry / rx)
    ctx.globalAlpha = alpha * (0.4 + rnd() * 0.45)
    ctx.fillStyle = g
    ctx.beginPath()
    ctx.arc(0, 0, rx, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }
  ctx.restore()
}

// Distant hills: a wet silhouette with a hard top edge and a dissolving foot.
export function farHills(ctx, cx, cy, w, h, alpha, seed = 9, color = 'rgba(70,74,84,1)') {
  if (alpha <= 0.002) return
  const rnd = mulberry32(seed * 22079)
  ctx.save()
  for (let k = 0; k < 3; k++) {
    const hw = w * (0.4 + rnd() * 0.45)
    const hh = h * (0.5 + rnd() * 0.7)
    const ox = cx + (rnd() - 0.5) * w * 0.8
    const oy = cy + (rnd() - 0.5) * h * 0.4
    const g = ctx.createLinearGradient(0, oy - hh, 0, oy + hh * 0.6)
    g.addColorStop(0, color)
    g.addColorStop(1, 'rgba(0,0,0,0)')
    ctx.globalAlpha = alpha * (0.1 + rnd() * 0.11)
    ctx.fillStyle = g
    ctx.beginPath()
    ctx.moveTo(ox - hw, oy + hh * 0.5)
    const steps = 26
    for (let i = 0; i <= steps; i++) {
      const t = i / steps
      const x = ox - hw + t * hw * 2
      const ridge = Math.sin(t * Math.PI) ** 0.75
      const bump = fbm1(t * 3 + k * 9, seed + k, 3) * 0.3
      ctx.lineTo(x, oy + hh * 0.5 - hh * (ridge * (0.85 + bump)))
    }
    ctx.lineTo(ox + hw, oy + hh * 0.6)
    ctx.closePath()
    ctx.fill()
  }
  ctx.restore()
}

// A spatter of spray — used for foam and for the seal's ink splat.
export function spatter(ctx, x, y, r, n, color, alpha, seed = 2) {
  const rnd = mulberry32(seed * 91193)
  ctx.save()
  ctx.fillStyle = color
  for (let i = 0; i < n; i++) {
    const a = rnd() * Math.PI * 2
    const d = Math.pow(rnd(), 0.6) * r
    const rr = 0.8 + rnd() * 2.6
    ctx.globalAlpha = alpha * (0.25 + rnd() * 0.75)
    ctx.beginPath()
    ctx.ellipse(x + Math.cos(a) * d, y + Math.sin(a) * d * 0.8, rr, rr * (0.6 + rnd() * 0.7), a, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.restore()
}
