const fs = require('fs');

let content = fs.readFileSync('frontend/src/components/BaseCard.vue', 'utf8');

// The script replaced the class successfully. But wait, we also need to fix inner glow shadow for light mode:
content = content.replace('shadow-[inset_1px_1px_0px_0px_rgba(255,255,255,0.15)]', 'shadow-[inset_1px_1px_0px_0px_rgba(0,0,0,0.05)] dark:shadow-[inset_1px_1px_0px_0px_rgba(255,255,255,0.15)]');

fs.writeFileSync('frontend/src/components/BaseCard.vue', content);
