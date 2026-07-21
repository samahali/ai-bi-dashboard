# ──────────────────────────────────────────────────────────────────
# Stage 1: development — Vite dev server with hot reload
# ──────────────────────────────────────────────────────────────────
FROM node:20-alpine AS development

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

# Source is mounted as a volume in dev
EXPOSE 5173
CMD ["npm", "run", "dev"]

# ──────────────────────────────────────────────────────────────────
# Stage 2: builder — production build
# ──────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile

COPY . .
RUN npm run build

# ──────────────────────────────────────────────────────────────────
# Stage 3: production — Nginx serving static files
# ──────────────────────────────────────────────────────────────────
FROM nginx:alpine AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config with SPA fallback
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# 127.0.0.1, not localhost — this image's nginx.conf only binds IPv4
# (listen 80, no [::]:80), but the container's /etc/hosts resolves
# "localhost" to ::1 first, so wget --spider http://localhost/ fails with
# connection refused even though the server is up and serving fine on IPv4.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
