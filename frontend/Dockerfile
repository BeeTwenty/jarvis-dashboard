FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

ARG BACKEND_URL=http://backend:8002
ENV NEXT_PUBLIC_BACKEND_URL=$BACKEND_URL

# Rewrite next.config.ts to point at the backend container
RUN sed -i "s|http://localhost:8002|${BACKEND_URL}|g" next.config.ts

RUN npm run build

# --- Production ---
FROM node:22-alpine

WORKDIR /app

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
