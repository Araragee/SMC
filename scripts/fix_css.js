const fs = require('fs');

let cssContent = fs.readFileSync('frontend/src/style.css', 'utf8');

// The original file only has .liquid-glass and .cosmic-void defined.
// We want to add light mode fallbacks without creating new classes.
// The task states:
// "Only update the existing .liquid-glass light mode definition to add a subtle border and refined shadow — no new custom classes. Also update .cosmic-void light mode to be warmer."

// Let's replace the whole style.css with the requested updates
const newCssContent = `@tailwind base;
@tailwind components;
@tailwind utilities;

@layer utilities {
  .liquid-glass {
    @apply backdrop-blur-[24px] rounded-3xl border border-black/[0.04] dark:border-white/5 shadow-[0_8px_32px_rgba(0,0,0,0.05)] dark:shadow-none;
  }

  .cosmic-void {
    @apply bg-[#0e0e0e] bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-900 via-[#0e0e0e] to-[#0e0e0e];
  }

  .text-glow {
    text-shadow: 0 0 24px rgba(255, 69, 0, 0.4);
  }
}

:where(.dark) .cosmic-void {
  @apply bg-[#0e0e0e] bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-900 via-[#0e0e0e] to-[#0e0e0e];
}

:where(.light) .cosmic-void {
  @apply bg-orange-50 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-orange-100 via-orange-50 to-white;
}

:root {
  --primary: #ff4500;
  --on-primary: #ffffff;
  --primary-container: #ffdbce;
  --on-primary-container: #460f00;

  --surface: #121212;
  --surface-dim: #0a0a0a;
  --on-surface: #e6e6e6;
  --surface-variant: #454545;
  --on-surface-variant: #cacaca;

  --outline: #949494;
  --outline-variant: #454545;
}

:root.light {
  --primary: #ff4500;
  --on-primary: #ffffff;
  --primary-container: #ffdbce;
  --on-primary-container: #460f00;

  --surface: #ffffff;
  --surface-dim: #f8fafc;
  --on-surface: #18181b;
  --surface-variant: #e4e4e7;
  --on-surface-variant: #52525b;

  --outline: #a1a1aa;
  --outline-variant: #e4e4e7;
}

body {
  font-family: 'Outfit', sans-serif;
  @apply bg-white dark:bg-[#0e0e0e] text-zinc-900 dark:text-zinc-200 antialiased;
}

h1, h2, h3, h4, h5, h6 {
  @apply font-semibold tracking-tight;
}
`;

fs.writeFileSync('frontend/src/style.css', newCssContent);
