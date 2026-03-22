import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  sassOptions: {},
  devIndicators: false,
  allowedDevOrigins: [process.env.DEV_ORIGIN || 'localhost'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8002/api/:path*',
      },
    ]
  },
}

export default nextConfig
