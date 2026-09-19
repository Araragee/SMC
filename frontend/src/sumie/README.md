# One Stroke — a sumi-e short, in code

A 51-second animated short. Nothing here is a bitmap, a video or a sound file:
the paper, every brushstroke and the whole soundtrack are generated from these
modules at render time.

Watch it in the app at **`/sumi-e`** (public route, no login).
Render the MP4 with `scripts/sumie` (see that folder's README).

## The story

One brushstroke paints four worlds — a pond with a koi and a frog, a bamboo
grove with a panda, a great wave with an octopus and a crab, and a cat curled
inside an ensō. A red seal stamp rides the wet end of the line between scenes
and plays with each character. The line fades, re-inks itself during the
pull-back to show it really was one stroke, the cast bows, the seal stamps the
corner and the brush signs the paper.

Cut for a feed: it **opens on the finale**, rewinds the ink back to blank paper,
plays the story, and ends on the opening frame, so it loops with no seam.

## The files

| file | what it holds |
| --- | --- |
| `rng.js` | seeded noise and easing — determinism lives here |
| `brush.js` | the ink: bristle bands, dry-brush streaks, wet bleed, pooling, washes, mist, far hills |
| `paper.js` | the washi sheet, baked once into an offscreen canvas |
| `cast.js` | all stroke geometry in world coordinates, including the spine that threads the four scenes |
| `story.js` | the timeline: paint schedule, ink clock, camera, the seal's choreography, bows, callouts |
| `film.js` | `renderFrame(ctx, t, env)` — the whole picture as a pure function of time |
| `audio.js` | the band: koto, bamboo flute, whistle, music box, bamboo blocks, plus a swish for every stroke |
| `audioWorker.js` | runs `audio.js` off the main thread for the web player |

## Two rules the code keeps

**Every frame is a pure function of `t`.** No state carries between frames, so
the film can be scrubbed, paused, rewound or rendered out of order by four
worker processes at once. The rewind is not a recording played backwards — it
is the same paint schedule read with the clock running the other way
(`inkTime()` in `story.js`).

**`t = 0` and `t = 51` are the same frame.** Ambient motion uses `loopPhase()`,
which is periodic over the full duration; the camera, the ink and the seal all
return to exactly where they started. 51 seconds is also exactly 28 bars at
131.76 BPM and exactly 1530 frames at 30fps, so the music meets the picture at
the loop point.

## Changing things

- **The signature**: `SIGN_NAME` in `film.js`.
- **Timing**: `T` and `CAM_KEYS` in `story.js`. Scene windows are one four-bar
  phrase each — keep them on phrase boundaries or the instrument hand-offs stop
  landing on bar lines.
- **The hook**: `HOOK` in `audio.js`, 32 eighth notes of D major pentatonic.
  `LEAD` picks which instrument plays it in each of the seven phrases.
- **A new character**: add stroke geometry in `cast.js` with a `group` name, give
  the group a pivot in `PIVOTS` and idle motion in `groupTransform()`.
