/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ['better-sqlite3']
  },
  // Disable problematic hot reload features
  reactStrictMode: false,
  swcMinify: false,
  webpack: (config, { dev, isServer }) => {
    // Disable file watching that causes zombie processes
    if (dev && !isServer) {
      config.watchOptions = {
        poll: false,
        ignored: /node_modules/
      };
    }
    if (isServer) {
      // Fix for better-sqlite3 in serverless environments
      config.externals.push('better-sqlite3');
    }
    return config;
  },
  images: {
    domains: ['maps.googleapis.com']
  },
  env: {
    NSW_PLANNING_API_BASE_URL: process.env.NSW_PLANNING_API_BASE_URL || 'https://api.apps1.nsw.gov.au/planning',
    GOOGLE_PLACES_API_KEY: process.env.GOOGLE_PLACES_API_KEY || '',
    DATABASE_PATH: process.env.DATABASE_PATH || '../nsw_planning.db'
  }
};

module.exports = nextConfig;