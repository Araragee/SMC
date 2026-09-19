// The timeline. Everything the film does at time t is decided here:
// what has been painted, where the camera is, what the seal is up to,
// and which callout is on screen.
//
// The cut is built for a feed loop: it opens on the finished painting,
// rewinds it back to blank paper, paints the story, and lands on the
// opening frame again at t = DURATION.

import { buildPath } from './brush.js'
import { SPINE, SCENE_STROKES, SCENES, SEAL_POS, WORLD } from './cast.js'
import { clamp, lerp, smoothstep, easeOut, easeInOut, noise1 } from './rng.js'

// 51 seconds is exactly 28 bars at this tempo and exactly 1530 frames, so the
// music, the picture and the loop point all land on the same instant.
export const DURATION = 51
export const FPS = 30
export const OUT = { w: 1080, h: 1350 }

export const PHRASE = DURATION / 7 // 7.2857s — one four-bar hook
export const BAR = PHRASE / 4
export const BEAT = BAR / 4
export const BPM = 60 / BEAT // 131.76 — a hair under the 132 it feels like

// The film is seven phrases: cold open + rewind, four scenes, two of finale.
export const T = {
  openEnd: 3.4, // cold open on the finished painting
  rewindEnd: 6.85, // ink runs backwards to blank paper
  brushLands: 7.05,
  musicStart: PHRASE, // scene 1 starts painting on the downbeat
  sceneSpan: PHRASE,
  paintOf: 6.05, // painting time inside each scene; the rest is travel
  finale: PHRASE * 5, // 36.43
  fade: [PHRASE * 5, 37.3], // the connecting line fades out
  reink: [37.3, 40.6], // ...and re-inks during the pull-back
  bows: [40.6, 43.5],
  stamp: PHRASE * 6, // the hero hops to the corner, on the downbeat
  stampHit: 44.15,
  sign: [44.6, 47.2],
  settle: 48.8,
}

export const sceneWindow = (i) => [PHRASE * (i + 1), PHRASE * (i + 2)]

// A phase that is periodic over the whole film, so t=0 and t=DURATION match
// pixel for pixel and the loop is invisible.
export const loopPhase = (t, cycles) => (2 * Math.PI * cycles * t) / DURATION

// ---------------------------------------------------------------------------
// paint schedule
// ---------------------------------------------------------------------------

function schedule(strokes, a, b) {
  const span = (b - a) * 0.94
  const weights = strokes.map((s) => Math.sqrt(buildPath(s).length) + 4)
  const total = weights.reduce((x, y) => x + y, 0) || 1
  let cursor = a
  strokes.forEach((s, i) => {
    const share = (weights[i] / total) * span
    s.start = cursor
    s.dur = Math.max(0.1, share * 1.5)
    cursor += share
  })
}

// Scene i: its spine segment goes down first (it *is* the scene), then the
// detail strokes, then the link that carries the brush to the next scene.
for (let i = 0; i < 4; i++) {
  const [a] = sceneWindow(i)
  const paintEnd = a + T.paintOf
  const spineSeg = SPINE.find((s) => s.scene === i)
  schedule([spineSeg], a, a + T.paintOf * 0.24)
  schedule(SCENE_STROKES[i], a + T.paintOf * 0.2, paintEnd)
  const link = SPINE.filter((s) => s.link)[i]
  if (link) schedule([link], paintEnd + 0.02, a + PHRASE)
}
const tailStroke = SPINE.find((s) => s.tail)
schedule([tailStroke], PHRASE * 4 + T.paintOf + 0.05, T.finale - 0.15)

export const PAINT_START = T.musicStart
export const PAINT_END = T.finale

export const FLAT_STROKES = [...SPINE, ...SCENE_STROKES.flat()].sort((p, q) => p.start - q.start)

/** Brush-swish cues for the soundtrack: one per stroke, plus the rewind. */
export function strokeCues() {
  return FLAT_STROKES.map((s) => ({
    t: s.start,
    dur: s.dur,
    len: buildPath(s).length,
    w: s.w,
    pan: clamp((s.pts[0][0] / WORLD.w - 0.5) * 1.4, -1, 1),
  }))
}

// ---------------------------------------------------------------------------
// ink time — the clock the painting itself runs on
// ---------------------------------------------------------------------------

export function inkTime(t) {
  if (t <= T.openEnd) return PAINT_END
  if (t < T.rewindEnd) {
    const r = easeInOut((t - T.openEnd) / (T.rewindEnd - T.openEnd))
    return lerp(PAINT_END, PAINT_START - 0.35, r)
  }
  if (t < T.musicStart) return PAINT_START - 0.35
  return t
}

export const strokeProgress = (s, it) => clamp((it - s.start) / s.dur, 0, 1)

/** The connecting line fades before the reveal, then re-inks itself. */
export function spineAlpha(t) {
  if (t < T.fade[0]) return 1
  if (t < T.fade[1]) return lerp(1, 0.1, smoothstep((t - T.fade[0]) / (T.fade[1] - T.fade[0])))
  if (t < T.reink[1]) return 0.1
  return 1
}

/** 0..1 position of the bright pulse that re-inks the line, or -1 for none. */
export function reinkPulse(t) {
  if (t < T.reink[0] || t > T.reink[1] + 0.35) return -1
  return clamp((t - T.reink[0]) / (T.reink[1] - T.reink[0]), 0, 1.0001)
}

// ---------------------------------------------------------------------------
// camera
// ---------------------------------------------------------------------------

const CAM_KEYS = [
  [0.0, 1080, 1350, 0.468],
  [3.4, 1080, 1350, 0.468],
  [5.4, 1040, 1290, 0.5],
  [7.0, 800, 980, 0.62],
  [7.2857, 620, 806, 0.8],
  [8.7, 600, 840, 0.98],
  [13.2, 640, 862, 1.04],
  [13.95, 1150, 650, 0.8],
  [14.5714, 1500, 830, 0.76],
  [15.9, 1560, 880, 0.94],
  [20.4, 1548, 920, 1.0],
  [21.25, 1320, 1480, 0.6],
  [21.8571, 760, 1800, 0.78],
  [23.2, 600, 1886, 1.0],
  [27.7, 646, 1912, 1.06],
  [28.45, 1070, 2010, 0.86],
  [29.1429, 1500, 1820, 0.8],
  [30.5, 1580, 1900, 0.98],
  [34.9, 1592, 1930, 1.06],
  [36.4286, 1580, 1902, 1.02],
  [37.3, 1500, 1820, 0.94],
  [40.6, 1080, 1350, 0.468],
  [44.0, 1080, 1382, 0.474],
  [47.6, 1080, 1350, 0.468],
  [51.0, 1080, 1350, 0.468],
]

export function camera(t) {
  let i = 0
  while (i < CAM_KEYS.length - 2 && t >= CAM_KEYS[i + 1][0]) i++
  const a = CAM_KEYS[i]
  const b = CAM_KEYS[i + 1]
  const f = easeInOut((t - a[0]) / Math.max(0.0001, b[0] - a[0]))
  const drift = Math.sin(loopPhase(t, 1))
  return {
    x: lerp(a[1], b[1], f) + drift * 7,
    y: lerp(a[2], b[2], f) + Math.cos(loopPhase(t, 1)) * 5,
    scale: lerp(a[3], b[3], f) * (1 + 0.004 * Math.cos(loopPhase(t, 1))),
  }
}

// ---------------------------------------------------------------------------
// the spine as one continuous line — used by the hero and by the re-ink pulse
// ---------------------------------------------------------------------------

let spineChain = null
function chain() {
  if (spineChain) return spineChain
  const segs = SPINE.map((s) => ({ s, path: buildPath(s) }))
  const total = segs.reduce((n, g) => n + g.path.length, 0)
  let acc = 0
  for (const g of segs) {
    g.u0 = acc / total
    acc += g.path.length
    g.u1 = acc / total
  }
  spineChain = { segs, total }
  return spineChain
}

/** A point at fraction u along the whole connecting line. */
export function spinePoint(u) {
  const c = chain()
  const uu = clamp(u, 0, 1)
  for (const g of c.segs) {
    if (uu <= g.u1 || g === c.segs[c.segs.length - 1]) {
      const local = clamp((uu - g.u0) / Math.max(1e-6, g.u1 - g.u0), 0, 1)
      const pts = g.path.pts
      const idx = clamp(Math.round(local * (pts.length - 1)), 0, pts.length - 1)
      const p = pts[idx]
      const q = pts[Math.min(pts.length - 1, idx + 1)]
      return { x: p.x, y: p.y, ang: Math.atan2(q.y - p.y, q.x - p.x), seg: g.s }
    }
  }
  return { x: 0, y: 0, ang: 0, seg: null }
}

/** How far along the whole line the brush has got, at a given ink time. */
export function spineHead(it) {
  const c = chain()
  let u = 0
  for (const g of c.segs) {
    const p = strokeProgress(g.s, it)
    if (p <= 0) break
    u = g.u0 + (g.u1 - g.u0) * p
    if (p < 1) break
  }
  return u
}

// ---------------------------------------------------------------------------
// the hero — a red seal stamp with opinions
// ---------------------------------------------------------------------------

// Where the seal breaks off the line to play with each character.
const PLAY = [
  { t0: 11.9, t1: 13.75, x: 620, y: 880, act: 'ride' }, // on the koi's back
  { t0: 19.2, t1: 21.05, x: 1712, y: 980, act: 'perch' }, // on the panda's shoulder
  { t0: 26.5, t1: 28.35, x: 590, y: 1812, act: 'bounce' }, // tossing with the octopus
  { t0: 33.8, t1: 35.65, x: 1606, y: 2072, act: 'curl' }, // curled up with the cat
]

export function heroState(t) {
  const it = inkTime(t)
  const bob = Math.sin(t * 7.1) * 5
  const base = { x: SEAL_POS.x, y: SEAL_POS.y, rot: 0, sx: 1, sy: 1, alpha: 1, stamped: true }

  // stamped in the corner: the opening frame, and the closing one
  if (t <= T.openEnd - 0.05 || t >= T.stamp + 0.75) return base

  // peeling itself off the paper as the ink rewinds
  if (t < T.rewindEnd) {
    const pop = clamp((t - (T.openEnd - 0.05)) / 0.45, 0, 1)
    const head = spinePoint(spineHead(it))
    const f = smoothstep(pop)
    return {
      x: lerp(SEAL_POS.x, head.x, f),
      y: lerp(SEAL_POS.y, head.y - 34, f) - Math.sin(f * Math.PI) * 120,
      rot: lerp(0, -0.5, f) + Math.sin(t * 20) * 0.12 * f,
      sx: 1,
      sy: 1,
      alpha: 1,
      stamped: false,
    }
  }

  // waiting on blank paper for the brush to come back down
  if (t < T.musicStart) {
    const p = spinePoint(0)
    const hop = t > T.brushLands ? Math.abs(Math.sin((t - T.brushLands) * 9)) * 26 : 0
    return { x: p.x, y: p.y - 30 - hop, rot: 0, sx: 1, sy: 1, alpha: 1, stamped: false }
  }

  // riding the re-inking pulse during the reveal, then taking its place
  const pulse = reinkPulse(t)
  if (t >= T.fade[1] && pulse >= 0 && pulse <= 1) {
    const p = spinePoint(pulse)
    return { x: p.x, y: p.y - 30, rot: Math.sin(t * 9) * 0.18, sx: 1, sy: 1, alpha: 1, stamped: false }
  }
  if (t >= T.reink[1] && t < T.stamp) {
    const p = spinePoint(1)
    const cheer = Math.abs(Math.sin((t - T.reink[1]) * 4.2))
    return { x: p.x, y: p.y - 34 - cheer * 34, rot: Math.sin(t * 5) * 0.2, sx: 1, sy: 1, alpha: 1, stamped: false }
  }
  // the hop to the corner and the stamp itself
  if (t >= T.stamp) {
    const f = clamp((t - T.stamp) / (T.stampHit - T.stamp), 0, 1)
    const from = spinePoint(1)
    const hit = clamp((t - T.stampHit) / 0.25, 0, 1)
    return {
      x: lerp(from.x, SEAL_POS.x, easeInOut(f)),
      y: lerp(from.y - 34, SEAL_POS.y, easeInOut(f)) - Math.sin(f * Math.PI) * 220,
      rot: lerp(-0.6, 0, easeOut(f)),
      sx: 1 + (1 - hit) * (f >= 1 ? 0.3 : 0) + hit * 0,
      sy: 1 - (f >= 1 ? (1 - hit) * 0.28 : 0),
      alpha: 1,
      stamped: hit > 0.4,
    }
  }

  // playing with whoever is on screen
  for (const p of PLAY) {
    if (t >= p.t0 && t <= p.t1) {
      const f = smoothstep((t - p.t0) / 0.45)
      const g = 1 - smoothstep((t - (p.t1 - 0.45)) / 0.45)
      const head = spinePoint(spineHead(it))
      const mix = Math.min(f, g)
      let ox = 0
      let oy = 0
      let rot = 0
      const k = t - p.t0
      if (p.act === 'ride') oy = Math.sin(k * 5.4) * 12
      if (p.act === 'perch') {
        oy = Math.sin(k * 8.8) * 7
        rot = Math.sin(k * 4.4) * 0.22
      }
      if (p.act === 'bounce') {
        oy = -Math.abs(Math.sin(k * 5.6)) * 58
        rot = Math.sin(k * 11) * 0.3
      }
      if (p.act === 'curl') {
        oy = Math.sin(k * 2.2) * 6
        rot = 0.25
      }
      return {
        x: lerp(head.x, p.x + ox, mix),
        y: lerp(head.y - 30, p.y + oy, mix),
        rot: rot * mix,
        sx: 1,
        sy: 1,
        alpha: 1,
        stamped: false,
      }
    }
  }

  // otherwise: riding the wet end of the line
  const head = spinePoint(spineHead(it))
  const moving = t < T.finale
  return {
    x: head.x,
    y: head.y - 32 - (moving ? Math.abs(Math.sin(t * 6.2)) * 14 : 0),
    rot: Math.sin(t * 4.4) * 0.16,
    sx: 1,
    sy: 1,
    alpha: 1,
    stamped: false,
  }
}

// ---------------------------------------------------------------------------
// the cast: idle life, playing along with the band, and the bows
// ---------------------------------------------------------------------------

export const PIVOTS = {
  koi: { x: 620, y: 950 },
  frog: { x: 330, y: 830 },
  pond: { x: 600, y: 860 },
  panda: { x: 1608, y: 1250 },
  flute: { x: 1608, y: 1250 },
  grove: { x: 1500, y: 900 },
  octopus: { x: 432, y: 1900 },
  whistle: { x: 432, y: 1900 },
  crab: { x: 912, y: 2150 },
  blocks: { x: 912, y: 2150 },
  wave: { x: 500, y: 1950 },
  cat: { x: 1580, y: 2020 },
  musicbox: { x: 1784, y: 2096 },
}

// who bows, and when
const BOWS = [
  { group: ['koi', 'frog'], t: 40.6 },
  { group: ['panda', 'flute'], t: 41.32 },
  { group: ['octopus', 'whistle', 'crab', 'blocks'], t: 42.04 },
  { group: ['cat', 'musicbox'], t: 42.76 },
]

/** Eighth-note pulse, used to make the cast play in time with the music. */
export function beatPulse(t, div = 1) {
  if (t < T.musicStart) return 0
  const b = ((t - T.musicStart) / (BEAT / div)) % 1
  return Math.pow(1 - b, 2.4)
}

export function groupTransform(group, t) {
  if (!group) return null
  const idle = { dx: 0, dy: 0, rot: 0, sx: 1, sy: 1 }
  const it = inkTime(t)
  const alive = it > PAINT_START
  const pulse = beatPulse(t, 2)
  const ph = loopPhase(t, 12)

  if (alive) {
    switch (group) {
      case 'koi':
        idle.rot = Math.sin(ph * 0.5) * 0.035 + pulse * 0.03
        idle.dx = Math.sin(ph * 0.5 + 1) * 7
        break
      case 'frog':
        idle.sy = 1 + pulse * 0.07
        idle.dy = -pulse * 7
        break
      case 'panda':
      case 'flute':
        idle.rot = Math.sin(ph * 0.25) * 0.02
        idle.dy = -pulse * 5
        break
      case 'octopus':
      case 'whistle':
        idle.dy = Math.sin(ph * 0.75) * 9 - pulse * 6
        idle.rot = Math.sin(ph * 0.4) * 0.03
        break
      case 'crab':
      case 'blocks':
        idle.dx = Math.sin(ph * 0.75 + 2) * 8
        idle.rot = pulse * 0.07
        break
      case 'cat':
        idle.sy = 1 + Math.sin(ph * 0.2) * 0.012
        break
      case 'musicbox':
        idle.rot = Math.sin(ph) * 0.02
        break
      default:
        break
    }
  }

  for (const b of BOWS) {
    if (!b.group.includes(group)) continue
    const f = clamp((t - b.t) / 0.62, 0, 1)
    if (f <= 0 || f >= 1) continue
    const dip = Math.sin(f * Math.PI)
    idle.rot += dip * 0.2
    idle.dy += dip * 26
    idle.sy *= 1 - dip * 0.05
  }
  return idle
}

// ---------------------------------------------------------------------------
// callouts — for everyone scrolling with the sound off
// ---------------------------------------------------------------------------

export const CALLOUTS = [
  { t0: 0.5, t1: 3.25, text: 'this is all ONE brushstroke', sub: 'no, really \u2014 watch', pos: 'bottom' },
  { t0: 3.7, t1: 6.55, text: 'rewinding the ink', sub: 'back to blank paper', pos: 'top' },
  { t0: 6.9, t1: 9.2, text: 'sound on', sub: 'the animals are the band \u00b7 132 bpm', pos: 'bottom' },
  { t0: 9.4, t1: 12.6, text: 'SCENE ONE \u00b7 the pond', sub: 'koi on koto', pos: 'bottom' },
  { t0: 16.7, t1: 19.9, text: 'SCENE TWO \u00b7 the grove', sub: 'panda on bamboo flute', pos: 'bottom' },
  { t0: 24.0, t1: 27.2, text: 'SCENE THREE \u00b7 the wave', sub: 'octopus on whistle, crab on blocks', pos: 'bottom' },
  { t0: 31.2, t1: 34.4, text: 'SCENE FOUR \u00b7 the ens\u014d', sub: 'cat on music box', pos: 'bottom' },
  { t0: 37.6, t1: 40.3, text: 'same line. the whole time.', sub: 'watch it re-ink', pos: 'top' },
  { t0: 40.7, t1: 43.4, text: 'take a bow', sub: 'full band, one take', pos: 'top' },
  { t0: 44.3, t1: 46.2, text: 'the seal signs off', sub: '', pos: 'top' },
  { t0: 46.8, t1: 49.8, text: 'one stroke \u00b7 four worlds', sub: 'and back to the top \u21bb', pos: 'top' },
]

export function activeCallouts(t) {
  const out = []
  for (const c of CALLOUTS) {
    if (t < c.t0 - 0.4 || t > c.t1 + 0.5) continue
    const inF = smoothstep((t - c.t0) / 0.42)
    const outF = 1 - smoothstep((t - c.t1) / 0.42)
    const a = Math.min(inF, outF)
    if (a <= 0.01) continue
    out.push({ ...c, alpha: a, rise: (1 - inF) * 18 })
  }
  return out
}

/** How far the signature has been written, 0..1. It is already there in the
 *  cold open, and it is the first thing the rewind takes back. */
export function signProgress(t) {
  if (t <= T.openEnd) return 1
  if (t < T.rewindEnd) return 1 - clamp((t - T.openEnd) / 0.8, 0, 1)
  if (t < T.sign[0]) return 0
  return clamp((t - T.sign[0]) / (T.sign[1] - T.sign[0]), 0, 1)
}

/** Atmosphere (wash, mist, hills) blooms in with the scene. */
export function atmosAlpha(i, it) {
  const [a] = sceneWindow(i)
  return clamp((it - (a - 0.2)) / 2.2, 0, 1)
}

export { SCENES, SEAL_POS, WORLD, noise1 }
