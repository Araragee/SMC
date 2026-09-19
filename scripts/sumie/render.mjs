#!/usr/bin/env node
// Render "One Stroke" to a 1080x1350 MP4.
//
//   cd scripts/sumie && npm install && node render.mjs
//
// The picture comes from ../../frontend/src/sumie (the same modules the web
// player uses) and the soundtrack is synthesised here, so the file and the
// page are always the same film. Frames are split across worker processes,
// each piping PNGs into its own ffmpeg segment; the segments are concatenated
// and the audio muxed in at the end.

import { spawn } from 'node:child_process'
import { mkdir, rm, writeFile, readdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import os from 'node:os'

const here = dirname(fileURLToPath(import.meta.url))
const ENGINE = resolve(here, '../../frontend/src/sumie')

let createCanvas
let ffmpegPath
try {
  ;({ createCanvas } = await import('@napi-rs/canvas'))
  ffmpegPath = (await import('ffmpeg-static')).default
} catch {
  console.error('Missing render dependencies. Run:  cd scripts/sumie && npm install')
  process.exit(1)
}

const { renderFrame } = await import(join(ENGINE, 'film.js'))
const { DURATION, FPS, OUT } = await import(join(ENGINE, 'story.js'))

// --- arguments --------------------------------------------------------------

const args = process.argv.slice(2)
const flag = (name, def) => {
  const i = args.indexOf('--' + name)
  return i >= 0 ? args[i + 1] : def
}
const has = (name) => args.includes('--' + name)

const fps = Number(flag('fps', FPS))
const scale = Number(flag('scale', has('preview') ? 0.5 : 1))
const width = Math.round(OUT.w * scale)
const height = Math.round(OUT.h * scale)
const totalFrames = Math.round(DURATION * fps)
const outPath = resolve(flag('out', join(here, 'out', 'one-stroke.mp4')))
const crf = flag('crf', has('preview') ? '28' : '19')
const workDir = join(here, '.work')

// --- worker mode ------------------------------------------------------------

if (has('worker')) {
  const index = Number(flag('worker', 0))
  const count = Number(flag('of', 1))
  const from = Math.floor((index * totalFrames) / count)
  const to = Math.floor(((index + 1) * totalFrames) / count)
  const seg = join(workDir, `seg${String(index).padStart(2, '0')}.mp4`)

  const ff = spawn(
    ffmpegPath,
    [
      '-hide_banner', '-loglevel', 'error', '-y',
      '-f', 'image2pipe', '-vcodec', 'png', '-r', String(fps), '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', String(crf),
      '-pix_fmt', 'yuv420p', '-g', '60', '-sc_threshold', '0',
      seg,
    ],
    { stdio: ['pipe', 'inherit', 'inherit'] },
  )

  const canvas = createCanvas(width, height)
  const ctx = canvas.getContext('2d')
  const env = { createCanvas }

  for (let f = from; f < to; f++) {
    const t = f / fps
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.clearRect(0, 0, width, height)
    ctx.save()
    ctx.scale(scale, scale)
    renderFrame(ctx, t, env, { width: OUT.w, height: OUT.h })
    ctx.restore()
    const buf = canvas.toBuffer('image/png')
    if (!ff.stdin.write(buf)) {
      await new Promise((r) => ff.stdin.once('drain', r))
    }
    if ((f - from) % 25 === 0) {
      process.send?.({ worker: index, done: f - from, total: to - from })
    }
  }
  ff.stdin.end()
  await new Promise((r) => ff.on('close', r))
  process.exit(0)
}

// --- master -----------------------------------------------------------------

const workers = Number(flag('workers', Math.min(4, Math.max(1, os.cpus().length))))
console.log(`One Stroke — ${width}x${height}, ${DURATION}s, ${fps}fps, ${totalFrames} frames, ${workers} workers`)

await rm(workDir, { recursive: true, force: true })
await mkdir(workDir, { recursive: true })
await mkdir(dirname(outPath), { recursive: true })

// 1. the soundtrack
console.log('· synthesising the band…')
const { renderSoundtrack, toWav } = await import(join(ENGINE, 'audio.js'))
const wavPath = join(workDir, 'track.wav')
await writeFile(wavPath, toWav(renderSoundtrack(48000)))

// 2. the frames
console.log('· painting…')
const started = Date.now()
const progress = new Array(workers).fill(0)
const totals = new Array(workers).fill(1)
let ticker = null

const runWorker = (i) =>
  new Promise((res, rej) => {
    const child = spawn(
      process.execPath,
      [fileURLToPath(import.meta.url), '--worker', String(i), '--of', String(workers),
       '--fps', String(fps), '--scale', String(scale), '--crf', String(crf)],
      { stdio: ['ignore', 'inherit', 'inherit', 'ipc'] },
    )
    child.on('message', (m) => {
      progress[i] = m.done
      totals[i] = m.total
    })
    child.on('close', (code) => {
      progress[i] = totals[i]
      code === 0 ? res() : rej(new Error(`worker ${i} exited ${code}`))
    })
  })

ticker = setInterval(() => {
  const done = progress.reduce((a, b) => a + b, 0)
  const pct = Math.round((done / totalFrames) * 100)
  const secs = (Date.now() - started) / 1000
  const eta = done > 20 ? Math.round((secs / done) * (totalFrames - done)) : null
  process.stdout.write(`\r  ${done}/${totalFrames} frames (${pct}%)${eta !== null ? `  eta ${eta}s` : ''}   `)
}, 1000)

await Promise.all(Array.from({ length: workers }, (_, i) => runWorker(i)))
clearInterval(ticker)
process.stdout.write('\n')

// 3. stitch, then mux the audio in
console.log('· stitching…')
const segs = (await readdir(workDir)).filter((f) => f.endsWith('.mp4')).sort()
const listPath = join(workDir, 'segments.txt')
await writeFile(listPath, segs.map((f) => `file '${join(workDir, f)}'`).join('\n'))

const run = (a) =>
  new Promise((res, rej) => {
    const p = spawn(ffmpegPath, ['-hide_banner', '-loglevel', 'error', '-y', ...a], { stdio: 'inherit' })
    p.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg failed: ' + a.join(' ')))))
  })

const silent = join(workDir, 'video.mp4')
await run(['-f', 'concat', '-safe', '0', '-i', listPath, '-c', 'copy', silent])
await run([
  '-i', silent, '-i', wavPath,
  '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
  '-movflags', '+faststart', '-shortest', outPath,
])
await rm(workDir, { recursive: true, force: true })

console.log(`\n✓ ${outPath}  (${Math.round((Date.now() - started) / 1000)}s)`)
