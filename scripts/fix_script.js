const fs = require('fs');
const path = require('path');

const srcDirs = [
  path.join(__dirname, 'frontend/src/components'),
  path.join(__dirname, 'frontend/src/views'),
  path.join(__dirname, 'frontend/src/layouts')
];

const swaps = [
  ['text-white', 'text-zinc-900', 'text-white'],
  ['bg-white/5', 'bg-black/[0.04]', 'bg-white/5'],
  ['bg-white/10', 'bg-black/[0.06]', 'bg-white/10'],
  ['bg-white/\\[0\\.02\\]', 'bg-black/[0.02]', 'bg-white/[0.02]'],
  ['border-white/10', 'border-black/[0.08]', 'border-white/10'],
  ['border-white/5', 'border-black/[0.04]', 'border-white/5'],
  ['text-zinc-400', 'text-zinc-500', 'text-zinc-400'],
  ['text-zinc-500', 'text-zinc-600', 'text-zinc-500'],
  ['text-zinc-600', 'text-zinc-500', 'text-zinc-600'],
  ['text-zinc-700', 'text-zinc-400', 'text-zinc-700'],
  ['bg-black/60', 'bg-black/30', 'bg-black/60'],
  ['bg-black/70', 'bg-black/30', 'bg-black/70'],
  ['bg-black/80', 'bg-black/30', 'bg-black/80']
];

function processFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  let original = content;

  // Use a regex that finds `class="..."` or `class='...'`
  content = content.replace(/class=(["'])(.*?)\1/g, (match, quote, innerClassString) => {
    // split the inner class string by whitespace
    let classes = innerClassString.split(/\s+/);
    let newClasses = [];

    for (let i = 0; i < classes.length; i++) {
        let cls = classes[i];
        if (!cls) continue;

        let replaced = false;
        for (const [targetStr, lightStr, darkTargetStr] of swaps) {
            // Need to unescape targetStr for comparison
            let unescapedTarget = targetStr.replace(/\\/g, '');
            if (cls === unescapedTarget) {
                newClasses.push(`${lightStr} dark:${darkTargetStr}`);
                replaced = true;
                break;
            }
        }
        if (!replaced) {
            newClasses.push(cls);
        }
    }

    return `class=${quote}${newClasses.join(' ')}${quote}`;
  });

  if (content !== original) {
      fs.writeFileSync(filePath, content, 'utf8');
      console.log('Updated: ' + filePath);
  }
}

function walk(dir) {
    if (!fs.existsSync(dir)) return;
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const fullPath = path.join(dir, file);
        if (fs.statSync(fullPath).isDirectory()) {
            walk(fullPath);
        } else if (fullPath.endsWith('.vue')) {
            processFile(fullPath);
        }
    }
}

srcDirs.forEach(walk);
