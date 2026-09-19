// The sumi-e film engine is plain ES modules (it also runs under node for the
// MP4 render, with no build step), so its public surface is declared here.

declare module '@/sumie/film.js' {
  export interface SumieEnv {
    createCanvas(width: number, height: number): HTMLCanvasElement
  }
  export function renderFrame(
    ctx: CanvasRenderingContext2D,
    time: number,
    env: SumieEnv,
    opts?: { width?: number; height?: number },
  ): void
  export const DURATION: number
  export const OUT: { w: number; h: number }
}

declare module '@/sumie/story.js' {
  export const DURATION: number
  export const FPS: number
  export const OUT: { w: number; h: number }
  export const BPM: number
  export const PHRASE: number
}

declare module '@/sumie/audio.js' {
  export interface SumieTrack {
    left: Float32Array
    right: Float32Array
    sampleRate: number
    duration: number
  }
  export function renderSoundtrack(sampleRate?: number): SumieTrack
  export function toWav(track: SumieTrack): Uint8Array
}
