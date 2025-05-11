/** @type {import('next').NextConfig} */
const path = require('path');

const nextConfig = {
  rewrites: async () => {
    // In Docker, use the service name for container-to-container communication
    // For local development, fall back to localhost
    // The NEXT_PUBLIC_API_URL environment variable can override this
    const backendUrl = process.env.NEXT_PUBLIC_API_URL ||
                      (process.env.NODE_ENV === 'production' ? 'http://backend:8000' : 'http://localhost:8000');

    console.log(`Using backend URL: ${backendUrl}`);

    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`
      }
    ]
  },

  // Add webpack configuration to resolve paths
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@common': path.resolve(__dirname, '../common'),
    };
    return config;
  }
}

module.exports = nextConfig