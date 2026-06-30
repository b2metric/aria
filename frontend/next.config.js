/** @type {import('next').NextConfig} */
const nextConfig = {
  // output: "standalone", // Disabled for dev environment to fix static file routing
  experimental: {
    // Disable turbopack if it's causing issues
  },
  async redirects() {
    return [
      {
        source: '/settings',
        destination: '/settings/profile',
        permanent: false,
      },
      {
        source: '/admin',
        destination: '/admin/users',
        permanent: false,
      },
    ];
  },
};

module.exports = nextConfig;
