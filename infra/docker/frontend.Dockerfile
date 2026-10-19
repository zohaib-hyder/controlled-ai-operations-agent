FROM node:26.12.0-alpine3.24 AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ENV NPM_CONFIG_AUDIT=false
ENV NPM_CONFIG_FUND=false
ENV NPM_CONFIG_UPDATE_NOTIFIER=false
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund --update-notifier=false
COPY frontend/ ./
RUN --network=none npm run build

FROM node:26.12.0-alpine3.24 AS runtime
WORKDIR /app
# Patch runtime OS libraries; npm is needed only in the build stage.
RUN apk add --upgrade --no-cache 'zlib>=1.3.2-r1' libcrypto3 libssl3 \
    && rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx \
        /usr/local/lib/node_modules/corepack /usr/local/bin/corepack \
        /opt/yarn-v* /usr/local/bin/yarn /usr/local/bin/yarnpkg \
        /usr/local/bin/pnpm /usr/local/bin/pnpx
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
