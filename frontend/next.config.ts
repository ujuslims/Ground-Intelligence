/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Proxies /api/* requests through the Next.js server to the backend, so the
  // browser only ever talks to this frontend's own origin. This is what lets
  // the backend's session cookie (HTTP-only, Rev 2 §I.1) work correctly even
  // though the frontend and backend are deployed as two separate services on
  // two different domains -- without this, the cookie would be a cross-site
  // cookie and get blocked by browsers' third-party cookie restrictions.
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

module.exports = nextConfig;
