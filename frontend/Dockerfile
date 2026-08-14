# ── Stage 1: base ────────────────────────────────────────────────────────────
FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --silent

# ── Stage 2: development ──────────────────────────────────────────────────────
FROM base AS development

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]

# ── Stage 3: build (for production, used in future chunks) ────────────────────
FROM base AS build

COPY . .
RUN npm run build

FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
