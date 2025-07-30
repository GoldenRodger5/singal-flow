/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    domains: ['localhost'],
  },
  env: {
    BACKEND_URL: process.env.BACKEND_URL || 'https://web-production-3e19d.up.railway.app',
  },
}

module.exports = nextConfig
