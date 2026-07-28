import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // @ts-expect-error - turbopack is a custom configuration property
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;

