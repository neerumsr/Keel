# Keel server (Keel-Lite on CPU, plus the Keel-Pro proxy). About 200 MB of app and models.
#   docker build -t keel .
#   docker run --rm -p 8080:8080 -e KEEL_SECRET=<a long random string> keel
# See docs/deployment.md.

FROM node:26-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM node:26-bookworm-slim
LABEL org.opencontainers.image.title="Keel" \
      org.opencontainers.image.description="Local typed decision model (System One wire)" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/neerumsr/Keel"
WORKDIR /app
ENV NODE_ENV=production \
    PORT=8080 \
    KEEL_HOST=0.0.0.0 \
    KEEL_SECRET_FILE=/data/secret
# The built server bundles its own dependencies and migrations; models load from ./models.
COPY --from=build /app/.output ./.output
COPY --from=build /app/models ./models
COPY --from=build /app/scripts/start.mjs ./scripts/start.mjs
COPY --from=build /app/src/lib/decider/auth.server.ts ./src/lib/decider/auth.server.ts
COPY --from=build /app/package.json ./package.json
RUN mkdir -p /data && chown node:node /data
USER node
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+process.env.PORT+'/api/v1/status').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "scripts/start.mjs"]
