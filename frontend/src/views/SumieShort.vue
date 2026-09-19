<template>
  <div class="sumie-page">
    <div class="stage">
      <canvas ref="canvasEl" class="film" :style="canvasStyle" @click="toggle"></canvas>

      <div v-if="!started" class="veil" @click="start">
        <button class="big-play" type="button" aria-label="Play">
          <svg viewBox="0 0 64 64" width="72" height="72" aria-hidden="true">
            <circle cx="32" cy="32" r="31" fill="none" stroke="currentColor" stroke-width="2" />
            <path d="M25 19 L47 32 L25 45 Z" fill="currentColor" />
          </svg>
        </button>
        <p class="veil-title">One Stroke</p>
        <p class="veil-sub">{{ booting ? 'tuning the band…' : 'a 51-second sumi-e short · sound on' }}</p>
      </div>
    </div>

    <div class="controls">
      <button class="ctl" type="button" @click="toggle">{{ playing ? 'Pause' : 'Play' }}</button>
      <button class="ctl" type="button" @click="restart">Restart</button>
      <button class="ctl" type="button" @click="muted = !muted">{{ muted ? 'Unmute' : 'Mute' }}</button>

      <input
        class="scrub"
        type="range"
        min="0"
        :max="duration"
        step="0.01"
        :value="time"
        @input="seek($event)"
      />
      <span class="clock">{{ time.toFixed(1) }} / {{ duration }}s</span>

      <a class="ctl link" :href="mp4Url" download>Download MP4</a>
    </div>

    <p class="note">
      Drawn live in a 2D canvas — every brushstroke, the paper, the seal and the whole band are
      generated in code. The MP4 is the same film rendered offline at 1080×1350.
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { renderFrame, type SumieEnv } from '@/sumie/film.js'
import { DURATION, OUT } from '@/sumie/story.js'

interface RawTrack {
  left: Float32Array<ArrayBuffer>
  right: Float32Array<ArrayBuffer>
  sampleRate: number
  duration: number
}

const canvasEl = ref<HTMLCanvasElement | null>(null)
const playing = ref(false)
const started = ref(false)
const booting = ref(false)
const muted = ref(false)
const time = ref(0)
const duration = DURATION
const mp4Url = '/sumie/one-stroke.mp4'

// The film is painted at a fraction of the output size and stretched to fit —
// it is a lot of vector ink per frame, and this keeps it at 30fps on a laptop.
let quality = 0.68
let ctx: CanvasRenderingContext2D | null = null
let raf = 0
let env: SumieEnv | null = null

// audio
let audioCtx: AudioContext | null = null
let buffer: AudioBuffer | null = null
let source: AudioBufferSourceNode | null = null
let gain: GainNode | null = null
let audioStart = 0 // audioCtx time at which t=0 happened
let clockBase = 0 // fallback clock when there is no audio

const canvasStyle = computed(() => ({ aspectRatio: `${OUT.w} / ${OUT.h}` }))

function sizeCanvas() {
  const c = canvasEl.value
  if (!c) return
  c.width = Math.round(OUT.w * quality)
  c.height = Math.round(OUT.h * quality)
  ctx = c.getContext('2d')
}

function draw(t: number) {
  if (!ctx || !env) return
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
  ctx.save()
  ctx.scale(quality, quality)
  renderFrame(ctx, t, env, { width: OUT.w, height: OUT.h })
  ctx.restore()
}

// --- audio ------------------------------------------------------------------

function synthesise(): Promise<AudioBuffer> {
  return new Promise<AudioBuffer>((resolve) => {
    let worker: Worker | null = null
    const finish = (data: RawTrack) => {
      const ac = audioCtx as AudioContext
      const buf = ac.createBuffer(2, data.left.length, data.sampleRate)
      buf.copyToChannel(data.left, 0)
      buf.copyToChannel(data.right, 1)
      resolve(buf)
    }
    try {
      worker = new Worker(new URL('../sumie/audioWorker.js', import.meta.url), { type: 'module' })
      const w = worker
      w.onmessage = (e: MessageEvent<RawTrack>) => {
        finish(e.data)
        w.terminate()
      }
      w.onerror = () => {
        w.terminate()
        void fallback()
      }
      w.postMessage({ sampleRate: audioCtx!.sampleRate })
    } catch {
      void fallback()
    }
    async function fallback() {
      const { renderSoundtrack } = await import('@/sumie/audio.js')
      finish(renderSoundtrack(audioCtx!.sampleRate) as unknown as RawTrack)
    }
  })
}

function stopSource() {
  if (source) {
    try {
      source.stop()
    } catch {
      /* already stopped */
    }
    source.disconnect()
    source = null
  }
}

function startSource(at: number) {
  if (!buffer || !audioCtx || !gain) return
  stopSource()
  source = audioCtx.createBufferSource()
  source.buffer = buffer
  source.loop = true
  source.connect(gain)
  source.start(0, at % duration)
  audioStart = audioCtx.currentTime - at
}

// --- transport ---------------------------------------------------------------

async function start() {
  if (booting.value) return
  booting.value = true
  try {
    const AC: typeof AudioContext | undefined =
      window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (AC && !audioCtx) {
      audioCtx = new AC()
      gain = audioCtx.createGain()
      gain.gain.value = muted.value ? 0 : 0.9
      gain.connect(audioCtx.destination)
      buffer = await synthesise()
    }
    if (audioCtx && audioCtx.state === 'suspended') await audioCtx.resume()
  } catch {
    audioCtx = null
  }
  booting.value = false
  started.value = true
  play()
}

function play() {
  playing.value = true
  if (audioCtx && buffer) startSource(time.value)
  else clockBase = performance.now() / 1000 - time.value
}

function pause() {
  playing.value = false
  stopSource()
}

function toggle() {
  if (!started.value) {
    void start()
    return
  }
  if (playing.value) pause()
  else play()
}

function restart() {
  time.value = 0
  if (!started.value) {
    void start()
    return
  }
  if (playing.value) play()
  else draw(0)
}

function seek(e: Event) {
  time.value = Number((e.target as HTMLInputElement).value)
  if (playing.value) play()
  else draw(time.value)
}

// --- loop --------------------------------------------------------------------

let frames = 0
let costSum = 0

function tick() {
  raf = requestAnimationFrame(tick)
  if (playing.value) {
    if (audioCtx && source) time.value = (audioCtx.currentTime - audioStart) % duration
    else time.value = (performance.now() / 1000 - clockBase) % duration
  }
  const t0 = performance.now()
  draw(time.value)
  // if the machine cannot keep up, paint smaller rather than stutter
  costSum += performance.now() - t0
  if (++frames === 30) {
    const avg = costSum / frames
    frames = 0
    costSum = 0
    if (avg > 26 && quality > 0.42) {
      quality = quality === 0.68 ? 0.54 : 0.42
      sizeCanvas()
    }
  }
}

onMounted(() => {
  env = { createCanvas: (w, h) => {
    const c = document.createElement('canvas')
    c.width = w
    c.height = h
    return c
  } }
  sizeCanvas()
  draw(0)
  raf = requestAnimationFrame(tick)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  stopSource()
  if (audioCtx) void audioCtx.close()
})
</script>

<style scoped>
.sumie-page {
  min-height: 100vh;
  background: #15161a;
  color: #e8e2d4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 18px;
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.stage {
  position: relative;
  max-height: 78vh;
  aspect-ratio: 1080 / 1350;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55);
  border-radius: 6px;
  overflow: hidden;
}
.film {
  display: block;
  height: 78vh;
  max-width: 92vw;
  width: auto;
  cursor: pointer;
  background: #f1ead9;
}
.veil {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: rgba(20, 18, 15, 0.42);
  cursor: pointer;
  color: #f4efe2;
}
.big-play {
  background: none;
  border: 0;
  color: inherit;
  cursor: pointer;
  padding: 0;
}
.veil-title {
  font-size: 30px;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin: 10px 0 0;
}
.veil-sub {
  font-size: 14px;
  opacity: 0.85;
  margin: 0;
}
.controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}
.ctl {
  background: #26262c;
  color: #e8e2d4;
  border: 1px solid #3a3a44;
  border-radius: 999px;
  padding: 7px 16px;
  font-size: 13px;
  cursor: pointer;
}
.ctl:hover {
  background: #32323a;
}
.link {
  text-decoration: none;
}
.scrub {
  width: min(360px, 60vw);
  accent-color: #c0392f;
}
.clock {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  opacity: 0.7;
  min-width: 96px;
}
.note {
  max-width: 620px;
  text-align: center;
  font-size: 12px;
  line-height: 1.6;
  opacity: 0.55;
  margin: 0;
}
</style>
