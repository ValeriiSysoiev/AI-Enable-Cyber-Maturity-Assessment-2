/** @type {import('next').NextConfig} */
const nextConfig = { 
  reactStrictMode: true,
  output: 'standalone'
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
