#!/bin/sh

# Default value for VITE_API_BASE_URL if not provided
if [ -z "$VITE_API_BASE_URL" ]; then
  VITE_API_BASE_URL="http://localhost:8000"
fi

# Create the env-config.js file
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  VITE_API_BASE_URL: "$VITE_API_BASE_URL"
};
EOF

# Start Nginx
nginx -g "daemon off;"
