/** @type {import('next').NextConfig} */

const nextConfig = {
  // Enable React Strict Mode for better development experience
  reactStrictMode: true,

  // Enable SWC minifier for better performance
  swcMinify: true,

  // Experimental features
  experimental: {
    // Enable Server Components
    serverComponentsExternalPackages: ['@prisma/client'],
    // Enable optimistic updates
    optimisticClientCache: true,
  },

  // Image configuration
  images: {
    // Allow external image sources
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.udemy.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'img-c.udemycdn.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'via.placeholder.com',
        pathname: '/**',
      },
    ],
    // Image formats
    formats: ['image/webp', 'image/avif'],
    // Image sizes
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },

  // Environment variables to expose to client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_APP_NAME: 'Free2Fetch',
    NEXT_PUBLIC_APP_VERSION: '1.0.0',
  },

  // Redirect configuration
  async redirects() {
    return [
      {
        source: '/dashboard',
        destination: '/dashboard/overview',
        permanent: false,
      },
      {
        source: '/admin',
        destination: '/admin/dashboard',
        permanent: false,
      },
    ]
  },

  // Headers configuration
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
      {
        source: '/api/(.*)',
        headers: [
          {
            key: 'Access-Control-Allow-Origin',
            value: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
          },
          {
            key: 'Access-Control-Allow-Methods',
            value: 'GET, POST, PUT, DELETE, OPTIONS',
          },
          {
            key: 'Access-Control-Allow-Headers',
            value: 'Content-Type, Authorization',
          },
        ],
      },
    ]
  },

  // Webpack configuration
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Bundle analyzer
    if (process.env.ANALYZE) {
      const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer')
      config.plugins.push(
        new BundleAnalyzerPlugin({
          analyzerMode: 'static',
          openAnalyzer: true,
        })
      )
    }

    return config
  },

  // TypeScript configuration
  typescript: {
    ignoreBuildErrors: false,
  },

  // ESLint configuration
  eslint: {
    ignoreDuringBuilds: false,
    dirs: ['pages', 'components', 'lib', 'hooks', 'utils'],
  },

  // Output configuration
  output: 'standalone',

  // PWA configuration (if needed)
  // pwa: {
  //   dest: 'public',
  //   disable: process.env.NODE_ENV === 'development',
  //   register: true,
  //   skipWaiting: true,
  // },

  // Compression
  compress: true,

  // Power by header
  poweredByHeader: false,

  // Trailing slash
  trailingSlash: false,

  // Generate ETags
  generateEtags: true,
}

module.exports = nextConfig