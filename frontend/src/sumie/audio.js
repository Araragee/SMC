// The band. Everything here is synthesised sample by sample — no samples, no
// libraries. The same code fills the AudioBuffer in the browser player and the
// WAV that gets muxed into the MP4, so the two always match.
//
// One four-bar hook, repeated every phrase on whichever instrument the scene
// on screen is holding: koto, bamboo flute, whistle, music box, and the whole
// band together for the cold open and the finale.

import { mulberry32 } from './rng.js'
import { DURATION, PHRASE, BAR, BEAT, T, strokeCues } from './story.js'

const midi = (n) => 440 * Math.pow(2, (n - 69) / 12)

// The hook, as 32 eighth notes over four bars. D major pentatonic, bouncy.
const HOOK = [
  74, 0, 76, 78, 0, 74, 71, 0,
  69, 0, 71, 74, 0, 0, 0, 0,
  78, 0, 76, 74, 0, 71, 69, 0,
  71, 0, 74, 0, 69, 0, 0, 0,
]
const BASS = [50, 47, 43, 45] // one root per bar
// a countermelody the band plays underneath in the tutti phrases
const PAD = [62, 59, 55, 57]

// which instrument carries the hook in each of the seven phrases
const LEAD = ['tutti', 'koto', 'flute', 'whistle', 'musicbox', 'tutti', 'tutti']

// ---------------------------------------------------------------------------
// voices
// ---------------------------------------------------------------------------

function mix(L, R, sr, t0, pan, n, gen) {
  const start = Math.max(0, Math.floor(t0 * sr))
  const gl = Math.sqrt(0.5 * (1 - pan))
  const gr = Math.sqrt(0.5 * (1 + pan))
  const len = L.length
  for (let i = 0; i < n; i++) {
    const j = start + i
    if (j >= len) break
    const v = gen(i)
    L[j] += v * gl
    R[j] += v * gr
  }
}

// Karplus-Strong: a plucked string. The koto, and the bass underneath it.
function pluck(L, R, sr, t0, freq, dur, amp, pan, seed, bright = 0.5) {
  const n = Math.floor(dur * sr)
  const N = Math.max(2, Math.round(sr / freq))
  const buf = new Float32Array(N)
  const rnd = mulberry32(seed >>> 0 || 1)
  let lp = 0
  for (let i = 0; i < N; i++) {
    const w = rnd() * 2 - 1
    lp += (w - lp) * (0.35 + bright * 0.5)
    buf[i] = lp
  }
  let idx = 0
  const damp = 0.5 + bright * 0.25
  mix(L, R, sr, t0, pan, n, (i) => {
    const cur = buf[idx]
    const nxt = buf[(idx + 1) % N]
    buf[idx] = (cur * damp + nxt * (1 - damp)) * 0.998
    idx = (idx + 1) % N
    const env = Math.exp((-3.6 * i) / n)
    return cur * amp * env
  })
}

// A bamboo flute: mostly air, a little tone, a slow breath in.
function flute(L, R, sr, t0, freq, dur, amp, pan, seed) {
  const n = Math.floor(dur * sr)
  const rnd = mulberry32(seed >>> 0 || 3)
  let ph = 0
  let noise = 0
  mix(L, R, sr, t0, pan, n, (i) => {
    const x = i / sr
    const u = i / n
    const vib = 1 + 0.006 * Math.sin(2 * Math.PI * 5.1 * x)
    ph += (2 * Math.PI * freq * vib) / sr
    const env = Math.min(1, x / 0.07) * Math.min(1, (1 - u) * 6) * (0.85 + 0.15 * Math.sin(2 * Math.PI * 4.6 * x))
    noise += ((rnd() * 2 - 1) - noise) * 0.12
    const tone = Math.sin(ph) + 0.22 * Math.sin(ph * 2) + 0.06 * Math.sin(ph * 3)
    return (tone * 0.85 + noise * 0.22) * amp * env
  })
}

// A whistle: nearly a sine, with a little swoop into the note.
function whistle(L, R, sr, t0, freq, dur, amp, pan) {
  const n = Math.floor(dur * sr)
  let ph = 0
  mix(L, R, sr, t0, pan, n, (i) => {
    const x = i / sr
    const u = i / n
    const bend = 1 - 0.035 * Math.exp(-x * 26)
    const vib = 1 + 0.01 * Math.sin(2 * Math.PI * 6.2 * x) * Math.min(1, x * 4)
    ph += (2 * Math.PI * freq * bend * vib) / sr
    const env = Math.min(1, x / 0.02) * Math.min(1, (1 - u) * 5)
    return (Math.sin(ph) + 0.12 * Math.sin(ph * 2)) * amp * env
  })
}

// A music box: inharmonic partials, struck and left to ring.
function musicbox(L, R, sr, t0, freq, dur, amp, pan) {
  const n = Math.floor(dur * sr)
  const parts = [1, 2.76, 5.4, 8.93]
  const gains = [1, 0.36, 0.16, 0.07]
  const decays = [4.2, 7, 11, 16]
  mix(L, R, sr, t0, pan, n, (i) => {
    const x = i / sr
    let v = 0
    for (let k = 0; k < parts.length; k++) {
      v += gains[k] * Math.sin(2 * Math.PI * freq * parts[k] * x) * Math.exp(-decays[k] * x)
    }
    const click = Math.exp(-x * 900) * 0.3
    return (v + click) * amp * Math.min(1, x / 0.003)
  })
}

// Bamboo blocks: a knock with a pitch to it.
function block(L, R, sr, t0, freq, amp, pan, seed) {
  const dur = 0.13
  const n = Math.floor(dur * sr)
  const rnd = mulberry32(seed >>> 0 || 5)
  let bp = 0
  let bp2 = 0
  mix(L, R, sr, t0, pan, n, (i) => {
    const x = i / sr
    const exc = (rnd() * 2 - 1) * Math.exp(-x * 420)
    // a pair of one-poles standing in for a resonant band
    bp += (exc - bp) * 0.55
    bp2 += (bp - bp2) * 0.55
    const tone = Math.sin(2 * Math.PI * freq * x) * Math.exp(-x * 42)
    return ((bp - bp2) * 7 + tone * 0.5) * amp
  })
}

// The brush itself: air over paper, once per stroke.
function swish(L, R, sr, t0, dur, amp, pan, seed) {
  const n = Math.floor(Math.min(dur, 0.7) * sr)
  if (n < 32) return
  const rnd = mulberry32(seed >>> 0 || 7)
  let hp = 0
  let lp = 0
  mix(L, R, sr, t0, pan, n, (i) => {
    const u = i / n
    const w = rnd() * 2 - 1
    lp += (w - lp) * 0.42
    hp += (lp - hp) * 0.035
    const band = lp - hp
    // fast in, tailing off — the shape of a brush being drawn across paper
    const env = Math.pow(Math.sin(Math.PI * Math.pow(u, 0.65)), 1.5)
    return band * amp * env
  })
}

// The seal landing on the paper.
function thump(L, R, sr, t0, amp) {
  const n = Math.floor(0.5 * sr)
  const rnd = mulberry32(31)
  let lp = 0
  mix(L, R, sr, t0, 0.35, n, (i) => {
    const x = i / sr
    const body = Math.sin(2 * Math.PI * 62 * x * (1 - 0.3 * x)) * Math.exp(-x * 9)
    const w = rnd() * 2 - 1
    lp += (w - lp) * 0.25
    const slap = lp * Math.exp(-x * 60) * 0.5
    return (body + slap) * amp
  })
}

// ---------------------------------------------------------------------------
// arrangement
// ---------------------------------------------------------------------------

function playNote(L, R, sr, inst, t, freq, dur, amp, pan, seed) {
  switch (inst) {
    case 'koto':
      pluck(L, R, sr, t, freq, dur * 1.9, amp * 2.5, pan, seed, 0.62)
      break
    case 'flute':
      flute(L, R, sr, t, freq, dur * 1.05, amp * 0.82, pan, seed)
      break
    case 'whistle':
      whistle(L, R, sr, t, freq, dur * 1.05, amp * 0.56, pan)
      break
    case 'musicbox':
      musicbox(L, R, sr, t, freq, Math.min(1.5, dur * 3), amp * 0.86, pan)
      break
    default:
      break
  }
}

function renderMusic(L, R, sr) {
  const EIGHTH = BEAT / 2
  for (let phrase = 0; phrase < 7; phrase++) {
    const p0 = phrase * PHRASE
    const lead = LEAD[phrase]
    const tutti = lead === 'tutti'

    // --- the hook -------------------------------------------------------
    for (let i = 0; i < 32; i++) {
      const note = HOOK[i]
      if (!note) continue
      const t = p0 + i * EIGHTH
      if (t >= DURATION) break
      // how long until the next note starts
      let span = 1
      while (i + span < 32 && !HOOK[i + span]) span++
      const dur = span * EIGHTH
      const f = midi(note)
      if (tutti) {
        musicbox(L, R, sr, t, f, Math.min(1.4, dur * 3), 0.3, -0.12)
        pluck(L, R, sr, t, f / 2, dur * 1.8, 0.2, 0.3, i * 31 + phrase, 0.6)
        flute(L, R, sr, t, f, dur, 0.12, 0.05, i * 17 + phrase)
      } else {
        playNote(L, R, sr, lead, t, f, dur, 0.46, lead === 'koto' ? -0.18 : 0.14, i * 13 + phrase * 7 + 1)
      }
    }

    // --- roots and pad ---------------------------------------------------
    for (let b = 0; b < 4; b++) {
      const tb = p0 + b * BAR
      if (tb >= DURATION) break
      pluck(L, R, sr, tb, midi(BASS[b]), BAR * 0.95, 0.3, -0.3, b * 97 + phrase * 5 + 2, 0.22)
      pluck(L, R, sr, tb + BEAT * 2, midi(BASS[b] + 7), BEAT * 1.6, 0.16, 0.34, b * 41 + phrase + 9, 0.3)
      if (tutti || lead === 'flute' || lead === 'musicbox') {
        flute(L, R, sr, tb, midi(PAD[b]), BAR * 0.9, 0.06, 0.4, b * 23 + phrase)
      }
    }

    // --- bamboo blocks: the crab's part ----------------------------------
    const blocksOn = tutti || lead === 'whistle'
    for (let e = 0; e < 16; e++) {
      const t = p0 + e * BEAT
      if (t >= DURATION) break
      if (blocksOn) {
        block(L, R, sr, t, e % 4 === 0 ? 900 : 1250, e % 4 === 0 ? 0.3 : 0.16, e % 2 ? 0.45 : -0.45, e + phrase * 3)
        if (e % 4 === 2) block(L, R, sr, t + BEAT / 2, 1600, 0.1, 0.5, e + 77)
      } else if (e % 4 === 2) {
        block(L, R, sr, t, 1250, 0.07, 0.4, e + phrase * 3)
      }
    }
  }
}

function renderSfx(L, R, sr) {
  // a swish for every stroke the brush lays down
  let lastSwish = -1
  const cues = strokeCues()
  for (const c of cues) {
    if (c.t < lastSwish + 0.1) continue
    lastSwish = c.t
    const amp = 0.028 + Math.min(0.055, c.len / 7000) + Math.min(0.03, c.w / 1500)
    swish(L, R, sr, c.t - 0.02, Math.min(0.62, c.dur * 1.1), amp, c.pan, Math.round(c.t * 1000) + 1)
  }
  // the rewind: the same strokes taken back, in reverse
  for (let i = 0; i < 26; i++) {
    const u = i / 26
    const t = T.openEnd + u * (T.rewindEnd - T.openEnd)
    swish(L, R, sr, t, 0.16, 0.045 * (1 - u * 0.4), Math.sin(i) * 0.6, i * 13 + 5)
  }
  // the brush touching back down
  swish(L, R, sr, T.brushLands, 0.4, 0.12, 0, 999)
  // the stamp
  thump(L, R, sr, T.stampHit, 0.5)
  // the signature, written
  for (let i = 0; i < 7; i++) {
    const t = T.sign[0] + (i / 7) * (T.sign[1] - T.sign[0])
    swish(L, R, sr, t, 0.3, 0.05, -0.4, i * 7 + 3)
  }
}

// A small room, so the band is not sitting inside your head.
function reverb(L, R, sr) {
  const combs = [1231, 1481, 1759, 2003]
  const gains = [0.36, 0.32, 0.29, 0.26]
  const wet = 0.2
  const out = [new Float32Array(L.length), new Float32Array(R.length)]
  for (let ch = 0; ch < 2; ch++) {
    const src = ch ? R : L
    const dst = out[ch]
    for (let c = 0; c < combs.length; c++) {
      const d = combs[c] + ch * 37
      const g = gains[c]
      const buf = new Float32Array(d)
      let idx = 0
      for (let i = 0; i < src.length; i++) {
        const y = buf[idx]
        buf[idx] = src[i] + y * g
        idx = idx + 1 === d ? 0 : idx + 1
        dst[i] += y * 0.25
      }
    }
  }
  for (let i = 0; i < L.length; i++) {
    L[i] = L[i] * (1 - wet) + out[0][i] * wet
    R[i] = R[i] * (1 - wet) + out[1][i] * wet
  }
}

/**
 * Render the whole soundtrack.
 * @returns {{left: Float32Array, right: Float32Array, sampleRate: number, duration: number}}
 */
export function renderSoundtrack(sampleRate = 48000) {
  const n = Math.round(DURATION * sampleRate)
  const L = new Float32Array(n)
  const R = new Float32Array(n)
  renderMusic(L, R, sampleRate)
  renderSfx(L, R, sampleRate)
  reverb(L, R, sampleRate)

  // soft clip, then normalise with a little headroom
  let peak = 0
  for (let i = 0; i < n; i++) {
    L[i] = Math.tanh(L[i] * 1.1)
    R[i] = Math.tanh(R[i] * 1.1)
    peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]))
  }
  const g = peak > 0 ? 0.89 / peak : 1
  for (let i = 0; i < n; i++) {
    L[i] *= g
    R[i] *= g
  }
  // a 12ms fade at each end kills the click at the loop seam
  const f = Math.round(0.012 * sampleRate)
  for (let i = 0; i < f; i++) {
    const k = i / f
    L[i] *= k
    R[i] *= k
    L[n - 1 - i] *= k
    R[n - 1 - i] *= k
  }
  return { left: L, right: R, sampleRate, duration: DURATION }
}

/** 16-bit stereo WAV, for handing to ffmpeg. */
export function toWav(track) {
  const { left, right, sampleRate } = track
  const n = left.length
  const bytes = 44 + n * 4
  const buf = new ArrayBuffer(bytes)
  const view = new DataView(buf)
  const str = (off, s) => {
    for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i))
  }
  str(0, 'RIFF')
  view.setUint32(4, bytes - 8, true)
  str(8, 'WAVE')
  str(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 2, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 4, true)
  view.setUint16(32, 4, true)
  view.setUint16(34, 16, true)
  str(36, 'data')
  view.setUint32(40, n * 4, true)
  let o = 44
  for (let i = 0; i < n; i++) {
    view.setInt16(o, Math.max(-1, Math.min(1, left[i])) * 32767, true)
    view.setInt16(o + 2, Math.max(-1, Math.min(1, right[i])) * 32767, true)
    o += 4
  }
  return new Uint8Array(buf)
}
