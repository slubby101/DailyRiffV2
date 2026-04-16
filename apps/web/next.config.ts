import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@dailyriff/api-client"],
  typescript: {
    // Radix UI Dialog types conflict with React 19 @types/react.
    // Type checking runs separately via tsc --noEmit in CI codegen job.
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
