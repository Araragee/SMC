const fs = require('fs');

let content = fs.readFileSync('frontend/src/components/ToastContainer.vue', 'utf8');

// Replace toast variants inline manually as per requirements
const replacements = [
  { search: /'bg-emerald-900\/80'/g, replace: "'bg-emerald-50/90 dark:bg-emerald-900/80'" },
  { search: /'border-emerald-500\/30'/g, replace: "'border-emerald-500/20 dark:border-emerald-500/30'" },
  { search: /'text-emerald-400'/g, replace: "'text-emerald-700 dark:text-emerald-400'" },
  { search: /'bg-red-900\/80'/g, replace: "'bg-red-50/90 dark:bg-red-900/80'" },
  { search: /'border-red-500\/30'/g, replace: "'border-red-500/20 dark:border-red-500/30'" },
  { search: /'text-red-400'/g, replace: "'text-red-700 dark:text-red-400'" },
  { search: /'bg-amber-900\/80'/g, replace: "'bg-amber-50/90 dark:bg-amber-900/80'" },
  { search: /'border-amber-500\/30'/g, replace: "'border-amber-500/20 dark:border-amber-500/30'" },
  { search: /'text-amber-400'/g, replace: "'text-amber-700 dark:text-amber-400'" },
  { search: /'bg-blue-900\/80'/g, replace: "'bg-blue-50/90 dark:bg-blue-900/80'" },
  { search: /'border-blue-500\/30'/g, replace: "'border-blue-500/20 dark:border-blue-500/30'" },
  { search: /'text-blue-400'/g, replace: "'text-blue-700 dark:text-blue-400'" },
  { search: /text-zinc-400/g, replace: "text-zinc-600 dark:text-zinc-400" },
  { search: /text-white/g, replace: "text-zinc-900 dark:text-white" }
];

replacements.forEach(r => {
  content = content.replace(r.search, r.replace);
});

fs.writeFileSync('frontend/src/components/ToastContainer.vue', content);
