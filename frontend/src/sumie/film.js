// The renderer. One pure function: given a 2D context and a time in seconds,
// draw that frame. Works against a browser canvas or node-canvas alike — the
// only thing it needs from the host is a way to make an offscreen canvas.

import { drawStroke, wash, mistBand, farHills, spatter, INK } from './brush.js'
import { getPaper } from './paper.js'
import { SPINE, SCENE_STROKES, SCENE_ATMOS, SIGN_POS } from './cast.js'
import {
  DURATION, OUT, T, inkTime, strokeProgress, spineAlpha, reinkPulse, spinePoint,
  camera, heroState, groupTransform, activeCallouts, signProgress, atmosAlpha,
  PIVOTS, FLAT_STROKES, loopPhase, sceneWindow,
} from './story.js'
import { clamp, lerp, smoothstep, noise1, mulberry32 } from './rng.js'

const PAPER_TONE = '#f1ead9'
const SEAL_RED = '#c0392f'

export { DURATION, OUT }

// ---------------------------------------------------------------------------

function applyGroup(ctx, group, t) {
  const g = groupTransform(group, t)
  if (!g) return false
  const p = PIVOTS[group]
  if (!p) return false
  if (g.dx === 0 && g.dy === 0 && g.rot === 0 && g.sx === 1 && g.sy === 1) return false
  ctx.save()
  ctx.translate(p.x + g.dx, p.y + g.dy)
  ctx.rotate(g.rot)
  ctx.scale(g.sx, g.sy)
  ctx.translate(-p.x, -p.y)
  return true
}

function drawSeal(ctx, s, t) {
  const size = 54
  ctx.save()
  ctx.translate(s.x, s.y)
  ctx.rotate(s.rot)
  ctx.scale(s.sx, s.sy)
  ctx.globalAlpha = s.alpha

  if (s.stamped) {
    // the wet halo a real seal leaves behind
    spatter(ctx, 0, 0, size * 0.95, 26, SEAL_RED, 0.22, 4)
  }

  // the stone itself
  const r = 9
  const w = size
  const h = size * 1.16
  ctx.fillStyle = SEAL_RED
  ctx.beginPath()
  ctx.moveTo(-w / 2 + r, -h / 2)
  ctx.arcTo(w / 2, -h / 2, w / 2, h / 2, r)
  ctx.arcTo(w / 2, h / 2, -w / 2, h / 2, r)
  ctx.arcTo(-w / 2, h / 2, -w / 2, -h / 2, r)
  ctx.arcTo(-w / 2, -h / 2, w / 2, -h / 2, r)
  ctx.closePath()
  ctx.fill()

  // uneven inking, so it never looks printed
  const rnd = mulberry32(99)
  ctx.globalAlpha = s.alpha * 0.18
  ctx.fillStyle = '#7d1f16'
  for (let i = 0; i < 12; i++) {
    const x = (rnd() - 0.5) * w
    const y = (rnd() - 0.5) * h
    ctx.beginPath()
    ctx.ellipse(x, y, 3 + rnd() * 7, 2 + rnd() * 6, rnd() * 3, 0, Math.PI * 2)
    ctx.fill()
  }

  // carved marks
  ctx.globalAlpha = s.alpha
  ctx.strokeStyle = PAPER_TONE
  ctx.lineWidth = 4.4
  ctx.lineCap = 'round'
  const marks = [
    [-13, -16, 13, -16],
    [-13, -2, 13, -2],
    [0, -16, 0, 14],
    [-13, 14, -2, 14],
  ]
  ctx.beginPath()
  for (const [x0, y0, x1, y1] of marks) {
    ctx.moveTo(x0, y0)
    ctx.lineTo(x1, y1)
  }
  ctx.stroke()

  if (!s.stamped) {
    // eyes and feet only while it is running about
    const blink = noise1(t * 2.3, 91) > 0.9 ? 0.15 : 1
    ctx.fillStyle = '#20120f'
    for (const ex of [-11, 11]) {
      ctx.beginPath()
      ctx.ellipse(ex, 22, 4.2, 4.6 * blink, 0, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.fillStyle = '#fff'
    for (const ex of [-12.4, 9.6]) {
      ctx.beginPath()
      ctx.ellipse(ex, 20.6, 1.4, 1.5 * blink, 0, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.strokeStyle = SEAL_RED
    ctx.lineWidth = 6
    const step = Math.sin(t * 11) * 4
    ctx.beginPath()
    ctx.moveTo(-10, h / 2 - 2)
    ctx.lineTo(-12, h / 2 + 8 + step)
    ctx.moveTo(10, h / 2 - 2)
    ctx.lineTo(12, h / 2 + 8 - step)
    ctx.stroke()
  }
  ctx.restore()
}

// The brush that is doing all of this: bamboo handle, loaded tuft.
function drawBrush(ctx, x, y, ang, alpha, size = 1) {
  if (alpha <= 0.01) return
  ctx.save()
  ctx.globalAlpha = alpha
  ctx.translate(x, y)
  ctx.rotate(ang)
  ctx.scale(size, size)
  ctx.strokeStyle = '#9b8158'
  ctx.lineWidth = 15
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(26, -62)
  ctx.lineTo(90, -215)
  ctx.stroke()
  ctx.strokeStyle = '#4a3a24'
  ctx.lineWidth = 17
  ctx.beginPath()
  ctx.moveTo(20, -50)
  ctx.lineTo(30, -72)
  ctx.stroke()
  ctx.fillStyle = INK
  ctx.beginPath()
  ctx.moveTo(0, 0)
  ctx.quadraticCurveTo(-2, -32, 14, -56)
  ctx.quadraticCurveTo(30, -34, 0, 0)
  ctx.fill()
  ctx.restore()
}

// ---------------------------------------------------------------------------

function drawScene(ctx, i, t, it, view) {
  const atmos = SCENE_ATMOS[i]
  const a = atmosAlpha(i, it)
  if (a > 0.01) {
    const drift = loopPhase(t, 2) + i
    farHills(ctx, atmos.hills.x, atmos.hills.y, atmos.hills.w, atmos.hills.h, a, i * 7 + 3)
    for (let k = 0; k < atmos.washes.length; k++) {
      const wsh = atmos.washes[k]
      wash(ctx, wsh.x, wsh.y, wsh.rx, wsh.ry, wsh.color, wsh.a * a, i * 11 + k + 2)
    }
    mistBand(ctx, atmos.mist.x + Math.sin(drift) * 40, atmos.mist.y, atmos.mist.w, atmos.mist.h, a * 0.85, drift, i + 4)
  }
  drawStrokeList(ctx, SCENE_STROKES[i], t, it, view)
}

function drawStrokeList(ctx, list, t, it, view) {
  let openGroup = null
  let opened = false
  for (const s of list) {
    const p = strokeProgress(s, it)
    if (p <= 0) continue
    const bb = s._path ? s._path.bbox : null
    if (bb && (bb.x1 < view.x0 || bb.x0 > view.x1 || bb.y1 < view.y0 || bb.y0 > view.y1)) continue
    if (s.group !== openGroup) {
      if (opened) ctx.restore()
      openGroup = s.group
      opened = applyGroup(ctx, openGroup, t)
    }
    drawStroke(ctx, s, p, { lod: view.lod })
  }
  if (opened) ctx.restore()
}

function drawSpine(ctx, t, it, view) {
  const alpha = spineAlpha(t)
  const pulse = reinkPulse(t)
  for (const s of SPINE) {
    const p = strokeProgress(s, it)
    if (p <= 0) continue
    let a = alpha
    // the re-ink sweeps along the line, restoring it as it goes
    if (pulse >= 0) {
      const chainFrac = spineFraction(s)
      a = pulse >= chainFrac.u1 ? 1 : pulse <= chainFrac.u0 ? 0.1 : lerp(0.1, 1, (pulse - chainFrac.u0) / (chainFrac.u1 - chainFrac.u0))
    }
    drawStroke(ctx, s, p, { alpha: a, lod: view.lod })
  }
  if (pulse >= 0 && pulse <= 1) {
    const q = spinePoint(pulse)
    ctx.save()
    ctx.globalAlpha = 0.5
    ctx.fillStyle = '#2b2b33'
    ctx.beginPath()
    ctx.ellipse(q.x, q.y, 26, 26, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
    spatter(ctx, q.x, q.y, 34, 8, INK, 0.3, Math.floor(pulse * 40) + 1)
  }
}

// cached per-segment position within the whole connecting line
let fracCache = null
function spineFraction(s) {
  if (!fracCache) {
    fracCache = new Map()
    let total = 0
    const lens = SPINE.map((x) => (x._path ? x._path.length : 1))
    for (const l of lens) total += l
    let acc = 0
    SPINE.forEach((x, i) => {
      fracCache.set(x, { u0: acc / total, u1: (acc + lens[i]) / total })
      acc += lens[i]
    })
  }
  return fracCache.get(s) || { u0: 0, u1: 1 }
}

// ---------------------------------------------------------------------------
// the signature
// ---------------------------------------------------------------------------

const SIGN_NAME = 'Dav Gonzales'

function drawSignature(ctx, t) {
  const p = signProgress(t)
  if (p <= 0) return
  ctx.save()
  ctx.translate(SIGN_POS.x, SIGN_POS.y)
  const font = '600 italic 112px "DejaVu Serif", "Georgia", serif'
  ctx.font = font
  const width = ctx.measureText(SIGN_NAME).width
  // reveal left to right, with the wet edge trailing the brush
  ctx.beginPath()
  ctx.rect(-24, -130, width * p + 14, 230)
  ctx.clip()
  ctx.fillStyle = INK
  for (const [dx, dy, a] of [
    [0, 0, 0.92],
    [1.6, 1.2, 0.3],
    [-1.4, -1, 0.22],
    [0, 2.6, 0.12],
  ]) {
    ctx.globalAlpha = a
    ctx.fillText(SIGN_NAME, dx, dy)
  }
  ctx.globalAlpha = 0.5
  ctx.font = '400 40px "DejaVu Serif", "Georgia", serif'
  if (p > 0.72) {
    ctx.globalAlpha = 0.5 * smoothstep((p - 0.72) / 0.28)
    ctx.fillText('one stroke, one breath', 6, 64)
  }
  ctx.restore()
  return { x: SIGN_POS.x + width * p, y: SIGN_POS.y - 20, active: p < 1 }
}

// ---------------------------------------------------------------------------
// screen-space furniture
// ---------------------------------------------------------------------------

function drawCallouts(ctx, t, W, H) {
  const list = activeCallouts(t)
  for (const c of list) {
    const bottom = c.pos === 'bottom'
    const y = (bottom ? H - 196 : 176) + c.rise
    ctx.save()
    ctx.globalAlpha = c.alpha
    ctx.textAlign = 'center'

    ctx.font = '700 54px "DejaVu Sans", "Helvetica Neue", sans-serif'
    const w = ctx.measureText(c.text).width
    // a halo of paper rather than a box, so the words sit *in* the painting
    ctx.lineJoin = 'round'
    ctx.strokeStyle = 'rgba(241,234,217,0.94)'
    ctx.lineWidth = 18
    ctx.strokeText(c.text, W / 2, y)
    ctx.fillStyle = '#1b1b20'
    ctx.fillText(c.text, W / 2, y)

    // a quick red underline, drawn like a flick of the brush
    ctx.strokeStyle = SEAL_RED
    ctx.lineWidth = 6
    ctx.lineCap = 'round'
    ctx.globalAlpha = c.alpha * 0.9
    ctx.beginPath()
    for (let i = 0; i <= 18; i++) {
      const f = i / 18
      const x = W / 2 - w / 2 + f * w
      const yy = y + 18 + Math.sin(f * 6 + t) * 2.4 - f * 3
      if (i === 0) ctx.moveTo(x, yy)
      else ctx.lineTo(x, yy)
    }
    ctx.stroke()

    if (c.sub) {
      ctx.globalAlpha = c.alpha * 0.85
      ctx.font = '500 34px "DejaVu Sans", "Helvetica Neue", sans-serif'
      ctx.strokeStyle = 'rgba(241,234,217,0.94)'
      ctx.lineWidth = 12
      ctx.strokeText(c.sub, W / 2, y + 58)
      ctx.fillStyle = '#3c3a38'
      ctx.fillText(c.sub, W / 2, y + 58)
    }
    ctx.restore()
  }
}

// ---------------------------------------------------------------------------

/**
 * Draw the frame at time `t` (seconds, 0..DURATION) into `ctx`.
 * `env.createCanvas(w,h)` is used once to bake the paper texture.
 */
export function renderFrame(ctx, time, env, opts = {}) {
  const W = opts.width || OUT.w
  const H = opts.height || OUT.h
  const t = ((time % DURATION) + DURATION) % DURATION
  const it = inkTime(t)
  const cam = camera(t)

  // Everything is drawn relative to whatever transform the caller set up, so
  // the player can paint the film at a fraction of the output size.
  ctx.save()
  ctx.globalAlpha = 1
  const paper = getPaper(env, W, H)
  ctx.drawImage(paper, 0, 0, W, H)

  // world -> screen
  ctx.translate(W / 2, H / 2)
  ctx.scale(cam.scale, cam.scale)
  ctx.translate(-cam.x, -cam.y)

  const halfW = W / 2 / cam.scale
  const halfH = H / 2 / cam.scale
  const view = {
    x0: cam.x - halfW - 60,
    x1: cam.x + halfW + 60,
    y0: cam.y - halfH - 60,
    y1: cam.y + halfH + 60,
    lod: clamp(cam.scale * 1.1, 0.42, 1),
  }

  for (let i = 0; i < 4; i++) {
    const [a] = sceneWindow(i)
    if (it < a - 0.3) continue
    drawScene(ctx, i, t, it, view)
  }
  drawSpine(ctx, t, it, view)

  const sign = drawSignature(ctx, t)

  const hero = heroState(t)
  drawSeal(ctx, hero, t)

  // the brush, visible whenever ink is being laid down — or taken back up
  let brushAt = null
  if (t > T.openEnd && t < T.finale) {
    let active = null
    for (const s of FLAT_STROKES) {
      if (it >= s.start && it <= s.start + s.dur) active = s
    }
    if (active) {
      const p = strokeProgress(active, it)
      const path = active._path
      const idx = clamp(Math.round(p * (path.pts.length - 1)), 0, path.pts.length - 1)
      const q = path.pts[idx]
      const rewinding = t < T.rewindEnd
      brushAt = {
        x: q.x,
        y: q.y,
        ang: -0.35 + Math.sin(t * (rewinding ? 26 : 3)) * (rewinding ? 0.25 : 0.1),
        alpha: rewinding ? 0.55 : 0.9,
      }
    }
  }
  if (sign && sign.active) brushAt = { x: sign.x, y: sign.y, ang: -0.3, alpha: 0.9 }
  if (brushAt && brushAt.alpha > 0) drawBrush(ctx, brushAt.x, brushAt.y, brushAt.ang, brushAt.alpha * 0.8, 0.78)

  ctx.restore()

  // --- screen space -------------------------------------------------------
  ctx.save()
  // the rewind gets a hint of a tape shuttle
  if (t > T.openEnd && t < T.rewindEnd) {
    const s = Math.sin((t - T.openEnd) * 40)
    ctx.globalAlpha = 0.06 + 0.05 * Math.abs(s)
    ctx.fillStyle = '#2a2622'
    for (let i = 0; i < 5; i++) {
      const y = ((t * 900 + i * 300) % (H + 200)) - 100
      ctx.fillRect(0, y, W, 2)
    }
    ctx.globalAlpha = 1
  }
  drawCallouts(ctx, t, W, H)
  ctx.restore()
}
