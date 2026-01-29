import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  experimental: {
    serverActions: {
      bodySizeLimit: "600mb",
      // Allow Server Actions from GitHub Codespaces and local development
      // Note: Wildcards not supported, use actual Codespaces hostname
      allowedOrigins: [
        'localhost:3000',
        'improved-goggles-r4qvq4qq95vpf59r7-3000.app.github.dev',
      ],
    },
  },
  // Allow large file uploads for API routes
  serverExternalPackages: [],
};

export default nextConfig;
