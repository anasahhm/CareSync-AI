import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  images: {
    domains: ["localhost", "api.gesturemed.ai"],
  },
};

export default nextConfig;
