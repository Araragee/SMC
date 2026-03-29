const fs = require('fs');

function addBlobs(filePath) {
    let content = fs.readFileSync(filePath, 'utf8');

    // Check if blobs already exist
    if (content.includes('bg-orange-300/20')) return;

    // Find the main container
    // Typically <div class="min-h-screen cosmic-void text-zinc-200">
    const blobHtml = `
    <!-- Decorative Light Mode Blobs -->
    <div class="fixed top-[-10%] left-[-10%] w-[500px] h-[500px] bg-orange-300/20 rounded-full blur-[150px] pointer-events-none dark:opacity-0 transition-opacity duration-500 z-0"></div>
    <div class="fixed bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-amber-300/20 rounded-full blur-[150px] pointer-events-none dark:opacity-0 transition-opacity duration-500 z-0"></div>
    `;

    content = content.replace(/<div class="(.*?)cosmic-void(.*?)">/, `<div class="$1cosmic-void$2">\n${blobHtml}`);
    fs.writeFileSync(filePath, content);
}

addBlobs('frontend/src/layouts/AdminLayout.vue');
addBlobs('frontend/src/layouts/StudentLayout.vue');
addBlobs('frontend/src/layouts/TeacherLayout.vue');
