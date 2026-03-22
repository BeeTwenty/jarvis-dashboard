import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  sassOptions: {},
  devIndicators: false,
  allowedDevOrigins: ['192.168.0.2'],
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
