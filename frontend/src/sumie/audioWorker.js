// Synthesising 51 seconds of band takes a couple of seconds, which is a
// couple of seconds of frozen UI if it happens on the main thread.

import { renderSoundtrack } from './audio.js'

self.onmessage = (e) => {
  const sampleRate = (e.data && e.data.sampleRate) || 44100
  const track = renderSoundtrack(sampleRate)
  self.postMessage(
    { left: track.left, right: track.right, sampleRate, duration: track.duration },
    [track.left.buffer, track.right.buffer],
  )
}
