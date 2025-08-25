/** @type {import('next').NextConfig} */
const nextConfig = { 
  reactStrictMode: true,
  output: 'standalone',
  
  // Production performance optimizations
  compress: true,
  poweredByHeader: false,
  
  // Enable experimental features for better performance
  experimental: {
    optimizePackageImports: ['react-window', 'recharts'],
  },

  // Static optimization
  swcMinify: true,
  
  // Optimize images and assets
  images: {
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 60,
  },
  
  // Bundle analyzer in development
  ...(process.env.ANALYZE === 'true' && {
    webpack: (config) => {
      config.resolve.alias = {
        ...config.resolve.alias,
      }
      return config
    }
  })
};
export default nextConfig;


// Security headers for CI
export async function headers() {
  return [
    {
      source: "/(.*)",
      headers: [
        { key: "x-frame-options", value: "SAMEORIGIN" },
        { key: "x-content-type-options", value: "nosniff" },
        { key: "referrer-policy", value: "no-referrer" }
      ]
    }
  ];
}
