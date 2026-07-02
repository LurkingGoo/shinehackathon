/** @type {import('next').NextConfig} */
const SCORING_SERVICE = process.env.SCORING_SERVICE_URL ?? "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  // /api/* proxies the FastAPI scoring-service — the seam swap. The client
  // stays on same-origin relative URLs (no CORS); only the source changed.
  async rewrites() {
    return [
      { source: "/api/caseload", destination: `${SCORING_SERVICE}/caseload` },
      { source: "/api/residents/:id", destination: `${SCORING_SERVICE}/residents/:id` },
      { source: "/api/incidents/stream", destination: `${SCORING_SERVICE}/incidents/stream` },
      { source: "/api/incidents/simulate", destination: `${SCORING_SERVICE}/incidents/simulate` },
      { source: "/api/incidents/trace", destination: `${SCORING_SERVICE}/incidents/trace` },
      { source: "/api/incidents/clear", destination: `${SCORING_SERVICE}/incidents/clear` },
    ];
  },
};

export default nextConfig;
