import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  // Keep portfolio/CI builds bounded on small Docker hosts.
  experimental: { cpus: 2 },
};

export default config;
