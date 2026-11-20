# Build stage
FROM node:22-slim AS builder

WORKDIR /app

ENV NODE_OPTIONS="--dns-result-order=ipv4first" \
    NPM_CONFIG_UPDATE_NOTIFIER=false

COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm config set fetch-retries 3 && \
    npm config set fetch-retry-mintimeout 5000 && \
    npm config set fetch-retry-maxtimeout 30000 && \
    timeout -k 10 180 npm ci --no-audit --no-fund --prefer-offline

COPY . .
RUN timeout -k 10 120 npm run build

# Runtime stage
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
