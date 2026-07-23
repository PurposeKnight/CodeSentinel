import type { NextConfig } from "next";

import path from "path";

const nextConfig: any = {
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
