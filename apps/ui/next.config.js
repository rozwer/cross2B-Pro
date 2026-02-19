/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  eslint: {
    dirs: ["src"],
  },
  async rewrites() {
    // Server-side rewrite uses internal Docker network URL
    // INTERNAL_API_URL is set at runtime for Docker, falls back to NEXT_PUBLIC_API_URL or localhost
    const apiUrl = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:28000";
    return {
      // Route Handlers take precedence over rewrites, but be explicit
      beforeFiles: [],
      afterFiles: [
        {
          // Proxy all /api/* to backend API
          source: "/api/:path*",
          destination: `${apiUrl}/api/:path*`,
        },
      ],
      fallback: [],
    };
  },
};

module.exports = nextConfig;
