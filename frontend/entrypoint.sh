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

# Build the CSP connect-src from the API origin so the SPA can reach a
# cross-origin backend. Include the ws/wss form for the messaging WebSocket.
WS_ORIGIN=$(echo "$VITE_API_BASE_URL" | sed -e 's|^http://|ws://|' -e 's|^https://|wss://|')
CONNECT_SRC="'self' $VITE_API_BASE_URL $WS_ORIGIN"
sed -i "s|__CONNECT_SRC__|$CONNECT_SRC|g" /etc/nginx/conf.d/default.conf

# Start Nginx
nginx -g "daemon off;"
