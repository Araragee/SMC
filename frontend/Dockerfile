# node 22.12+ required: vite@8 + rolldown's native binding declare engines
# >=22.12, and npm silently SKIPS optional deps that fail the engine check —
# which is what left @rolldown/binding-linux-* missing on 22.11.0.
# ponytail: floating 22-slim tracks latest LTS 22.x; pin a digest if a future
# 22.x ever regresses the build.
FROM node:22-slim AS build-stage

RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ponytail: copy only package.json (NOT the macOS-generated package-lock.json)
# so npm resolves rolldown's platform-native binding for the build arch. With
# the lockfile present, npm's optional-deps bug (npm/cli#4828) skips
# @rolldown/binding-linux-* and `vite build` dies with MODULE_NOT_FOUND.
# Upgrade path: generate package-lock.json inside linux and switch to `npm ci`.
COPY package.json ./
RUN npm install --legacy-peer-deps

COPY . .

RUN npm run build

FROM nginx:stable-alpine AS production-stage

COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

CMD ["/entrypoint.sh"]
