# Rendering "One Stroke" to MP4

Renders the short from `frontend/src/sumie` to a 1080x1350 H.264 MP4 with the
synthesised soundtrack muxed in. The picture code is shared with the web player
at `/sumi-e`, so the file and the page are always the same film.

```bash
cd scripts/sumie
npm install          # @napi-rs/canvas + a static ffmpeg build
npm run render       # -> out/one-stroke.mp4   (1080x1350, 30fps, 51s)
npm run preview      # -> out/preview.mp4      (half size, faster)
```

Options:

```
--out <path>     where to write             (default out/one-stroke.mp4)
--fps <n>        frame rate                 (default 30)
--scale <f>      fraction of 1080x1350      (default 1)
--crf <n>        x264 quality, lower=bigger (default 19)
--workers <n>    parallel renderers         (default: number of cores, max 4)
```

Frames are split across worker processes, each piping PNGs into its own ffmpeg
segment; the segments are concatenated and the audio muxed in at the end. This
works only because every frame is a pure function of time — see the note in
`frontend/src/sumie/README.md`.

A full render is about 1530 frames and takes a few minutes on four cores.
`node_modules/` and `out/` are not committed.
