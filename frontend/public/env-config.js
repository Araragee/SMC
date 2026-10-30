// Runtime API-origin override, read by src/typescript/constants.ts.
//
// Intentionally empty. The nginx image's entrypoint.sh rewrites this file at
// container start from $VITE_API_BASE_URL, which is the only situation where
// it carries a value. A host that builds the bundle itself (Render's static
// site) bakes VITE_API_BASE_URL in at build time and never rewrites this file,
// so a hardcoded value here would be a trap: if the build-time variable were
// ever missing, every visitor's API calls would be sent to their own machine
// instead of falling back to the page's origin.
window._env_ = {
  VITE_API_BASE_URL: ''
};
