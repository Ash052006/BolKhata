# Frontend Dockerfile — multi-stage build + Nginx production server
# Stage 1: build the Vite bundle
FROM node:24-slim AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: serve with Nginx
FROM nginx:1.27-alpine AS runtime

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Install our config (see nginx.conf for proxy details)
COPY nginx.conf /etc/nginx/conf.d/bolkhata.conf

# Copy the built static files
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
