import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  experimental: {
    serverActions: {
      bodySizeLimit: "600mb",
      // Allow Server Actions from GitHub Codespaces forwarded URLs
      allowedOrigins: [
        'localhost:3000',
        '*.app.github.dev', // GitHub Codespaces
        '*.preview.app.github.dev',
      ],
    },
  },
};

export default nextConfig;
