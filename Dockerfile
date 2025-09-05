# Node 20 LTS on Alpine
FROM node:20-alpine

WORKDIR /app

# Install production deps first (better caching)
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

# Copy app
COPY . .

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD wget -qO- http://localhost:3000/version || exit 1

CMD ["node", "server.js"]