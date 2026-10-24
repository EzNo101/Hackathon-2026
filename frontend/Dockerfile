# Build stage: npm ci + tsc -b + vite build -> statická složka dist/
FROM node:22-alpine AS build

WORKDIR /app

# Nejdřív jen manifesty, aby se závislosti cachovaly mezi buildy.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Build-time proměnná: Vite ji zapíše do bundlu. Prázdná hodnota = relativní cesta.
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Runtime stage: jen nginx se statickými soubory, bez Node.js.
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
