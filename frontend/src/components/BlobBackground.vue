<script setup lang="ts">
/**
 * BlobBackground — iOS 26-inspired animated orb background
 * 
 * Dark mode: cosmic deep black with glowing orange/red blobs
 * Light mode: warm white with soft peach/amber cloud blobs
 * 
 * Responds automatically to .dark class on <html>
 */
</script>

<template>
  <div class="blob-root">
    <!-- Fixed canvas behind all content -->
    <div class="blob-canvas" aria-hidden="true">
      <div class="blob blob-1" />
      <div class="blob blob-2" />
      <div class="blob blob-3" />
      <div class="blob blob-4" />
      <div class="blob blob-5" />
    </div>

    <!-- Slotted content sits above the blobs -->
    <div class="blob-content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
/* Root wrapper — sets the page background via CSS variable */
.blob-root {
  position: relative;
  min-height: 100vh;
  isolation: isolate;
}

/* ============================================================
   Canvas — fixed behind everything, full viewport
   ============================================================ */
.blob-canvas {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  /* Light mode base */
  background: #fffbfe;
}

/* Content above the canvas */
.blob-content {
  position: relative;
  z-index: 0;
}

/* ============================================================
   Blob base styles
   ============================================================ */
.blob {
  position: absolute;
  border-radius: 50%;
  will-change: transform, opacity;
  pointer-events: none;
}

/* ============================================================
   Blob 1 — Large, top-left anchor
   Light: soft peach-orange
   Dark : deep orange glow
   ============================================================ */
.blob-1 {
  width: clamp(380px, 45vw, 620px);
  height: clamp(380px, 45vw, 620px);
  top: -12%;
  left: -8%;
  background: radial-gradient(
    ellipse at center,
    rgba(255, 144, 109, 0.60) 0%,
    rgba(255, 120, 80,  0.30) 40%,
    transparent 72%
  );
  filter: blur(72px);
  animation: pulse-1 15s ease-in-out infinite;
}
/* ============================================================
   Blob 2 — Medium, top-right
   Light: warm amber / golden
   Dark : deep red-orange
   ============================================================ */
.blob-2 {
  width: clamp(300px, 36vw, 500px);
  height: clamp(300px, 36vw, 500px);
  top: -6%;
  right: -6%;
  background: radial-gradient(
    ellipse at center,
    rgba(255, 185, 80,  0.55) 0%,
    rgba(255, 150, 60,  0.25) 40%,
    transparent 72%
  );
  filter: blur(88px);
  animation: pulse-2 20s ease-in-out infinite;
}
/* ============================================================
   Blob 3 — Large, bottom-center (the cloud floor)
   Light: coral / soft rose-orange
   Dark : ember orange
   ============================================================ */
.blob-3 {
  width: clamp(480px, 60vw, 800px);
  height: clamp(480px, 60vw, 800px);
  bottom: -25%;
  left: 15%;
  background: radial-gradient(
    ellipse at center,
    rgba(255, 120, 80,  0.45) 0%,
    rgba(255, 100, 60,  0.20) 45%,
    transparent 72%
  );
  filter: blur(100px);
  animation: pulse-3 24s ease-in-out infinite;
}
/* ============================================================
   Blob 4 — Small, mid-right drift
   Light: golden yellow
   Dark : amber glow
   ============================================================ */
.blob-4 {
  width: clamp(220px, 28vw, 400px);
  height: clamp(220px, 28vw, 400px);
  top: 38%;
  right: 4%;
  background: radial-gradient(
    ellipse at center,
    rgba(255, 215, 100, 0.50) 0%,
    rgba(255, 185, 60,  0.20) 40%,
    transparent 72%
  );
  filter: blur(72px);
  animation: pulse-4 17s ease-in-out infinite;
}
/* ============================================================
   Blob 5 — Medium, mid-left
   Light: rose-peach
   Dark : crimson
   ============================================================ */
.blob-5 {
  width: clamp(260px, 32vw, 450px);
  height: clamp(260px, 32vw, 450px);
  top: 52%;
  left: 2%;
  background: radial-gradient(
    ellipse at center,
    rgba(255, 150, 120, 0.45) 0%,
    rgba(255, 120, 90,  0.18) 40%,
    transparent 72%
  );
  filter: blur(80px);
  animation: pulse-5 13s ease-in-out infinite;
}
/* ============================================================
   Animations — each blob has its own rhythm
   ============================================================ */
@keyframes pulse-1 {
  0%,  100% { transform: translate(0px,   0px)   scale(1.00); opacity: 0.85; }
  20%       { transform: translate(55px,  35px)  scale(1.12); opacity: 1.00; }
  50%       { transform: translate(-30px, 65px)  scale(0.92); opacity: 0.72; }
  75%       { transform: translate(20px,  -25px) scale(1.06); opacity: 0.90; }
}

@keyframes pulse-2 {
  0%,  100% { transform: translate(0px,   0px)   scale(1.00); opacity: 0.78; }
  30%       { transform: translate(-70px, 55px)  scale(1.10); opacity: 0.95; }
  60%       { transform: translate(35px,  -40px) scale(0.90); opacity: 0.65; }
  85%       { transform: translate(-20px, 30px)  scale(1.04); opacity: 0.82; }
}

@keyframes pulse-3 {
  0%,  100% { transform: translate(0px,   0px)   scale(1.00); opacity: 0.70; }
  25%       { transform: translate(75px,  -50px) scale(1.15); opacity: 0.88; }
  55%       { transform: translate(-55px, 30px)  scale(0.88); opacity: 0.58; }
  80%       { transform: translate(30px,  70px)  scale(1.08); opacity: 0.78; }
}

@keyframes pulse-4 {
  0%,  100% { transform: translate(0px,   0px)   scale(1.00); opacity: 0.60; }
  35%       { transform: translate(-60px, -70px) scale(1.18); opacity: 0.78; }
  65%       { transform: translate(40px,  50px)  scale(0.85); opacity: 0.50; }
}

@keyframes pulse-5 {
  0%,  100% { transform: translate(0px,   0px)   scale(1.00); opacity: 0.65; }
  40%       { transform: translate(65px,  -45px) scale(1.14); opacity: 0.82; }
  70%       { transform: translate(-35px, 55px)  scale(0.90); opacity: 0.55; }
}

/* Reduce motion for accessibility */
@media (prefers-reduced-motion: reduce) {
  .blob { animation: none !important; }
}
</style>

<!-- Non-scoped: dark mode overrides need to match .dark on <html> -->
<style>
.dark .blob-canvas {
  background: #0e0e0e;
}

.dark .blob-1 {
  background: radial-gradient(
    ellipse at center,
    rgba(255, 69,  0,  0.55) 0%,
    rgba(200, 40,  0,  0.25) 40%,
    transparent 72%
  );
}

.dark .blob-2 {
  background: radial-gradient(
    ellipse at center,
    rgba(230, 50,  0,  0.45) 0%,
    rgba(180, 30,  0,  0.20) 40%,
    transparent 72%
  );
}

.dark .blob-3 {
  background: radial-gradient(
    ellipse at center,
    rgba(255, 100, 40,  0.40) 0%,
    rgba(200, 60,  10,  0.18) 45%,
    transparent 72%
  );
}

.dark .blob-4 {
  background: radial-gradient(
    ellipse at center,
    rgba(255, 154, 61,  0.30) 0%,
    rgba(200, 100, 20,  0.12) 40%,
    transparent 72%
  );
}

.dark .blob-5 {
  background: radial-gradient(
    ellipse at center,
    rgba(200, 40,  0,   0.35) 0%,
    rgba(150, 20,  0,   0.14) 40%,
    transparent 72%
  );
}
</style>
