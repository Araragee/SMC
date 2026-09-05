<script setup lang="ts">
/**
 * AppBackground (kept under its original filename so layouts need no change).
 *
 * Was five animated, glowing orbs drifting behind every page. Replaced with a
 * single static pastel wash, for three reasons:
 *
 *  - Continuous background animation on every route is a real cost: five
 *    large blurred elements repaint forever, on battery, behind content
 *    nobody is looking at.
 *  - Moving colour behind text lowers effective contrast and is a known
 *    trigger for motion sensitivity and vestibular disorders.
 *  - It is decoration competing with the data the page exists to show.
 *
 * What is left is a fixed, very low-contrast tint anchored to the top of the
 * viewport — enough to keep the page from reading as flat white, not enough
 * to interfere with anything on top of it.
 */
</script>

<template>
  <div class="app-bg-root">
    <div class="app-bg-wash" aria-hidden="true" />
    <div class="app-bg-content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.app-bg-root {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh; /* accounts for mobile browser chrome */
  isolation: isolate;
  background: var(--background);
}

.app-bg-wash {
  position: fixed;
  inset: 0;
  z-index: -1;
  background:
    /* Warm apricot at the top-left, sage at the top-right; both fade out
       well before the fold so content sits on the flat surface colour. */
    radial-gradient(60rem 32rem at 12% -8%, rgb(var(--primary-rgb) / 0.1), transparent 70%),
    radial-gradient(52rem 28rem at 88% -4%, rgb(var(--secondary-rgb) / 0.1), transparent 70%),
    var(--background);
  opacity: 1;
}

/* The tint is decorative; drop it entirely when the user asks for higher
   contrast, so text sits on a known flat colour. */
@media (prefers-contrast: more) {
  .app-bg-wash {
    background: var(--background);
  }
}

.app-bg-content {
  position: relative;
  z-index: 0;
}
</style>
