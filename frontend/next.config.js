/** @type {import('next').NextConfig} */
const nextConfig = {
  // output: "standalone", // Disabled for dev environment to fix static file routing
  experimental: {
    // Disable turbopack if it's causing issues
  }
};

module.exports = nextConfig;
