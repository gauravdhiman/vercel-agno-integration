# Build stage
FROM node:18-alpine AS builder

# Install pnpm
RUN npm install -g pnpm

# Set working directory
WORKDIR /app

# Copy package.json and pnpm-lock.yaml
COPY ui/package.json ui/pnpm-lock.yaml ./

# Install dependencies without frozen-lockfile to allow for package.json changes
RUN pnpm install --no-frozen-lockfile

# Install missing tailwind typography plugin if not already installed
RUN pnpm add -D @tailwindcss/typography

# Copy the UI code first
COPY ui/ .

# Copy the common directory at the same level as the UI directory
# This maintains the relative path structure expected by the imports
COPY common/ /app/../common/

# Build the application
RUN pnpm build

# Production stage
FROM node:18-alpine AS runner

# Set working directory
WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Set environment variables
ENV NODE_ENV=production

# Copy built application from builder stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/pnpm-lock.yaml ./pnpm-lock.yaml
COPY --from=builder /app/next.config.js ./next.config.js

# Copy the common directory at the same level as the UI directory
# This maintains the relative path structure expected by the imports
COPY --from=builder /app/../common /app/../common

# Install production dependencies only without frozen-lockfile
RUN pnpm install --no-frozen-lockfile --prod

# Install missing tailwind typography plugin if not already installed
RUN pnpm add -D @tailwindcss/typography

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["pnpm", "start"]
