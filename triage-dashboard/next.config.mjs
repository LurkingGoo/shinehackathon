/** @type {import('next').NextConfig} */
const RAW_SCORING = process.env.SCORING_SERVICE_URL ?? "http://127.0.0.1:8000";
// A host reference (e.g. Render's `fromService` property:host) arrives without a
// scheme; the rewrite destinations need a full URL, so default a bare host to https.
const SCORING_SERVICE = /^https?:\/\//.test(RAW_SCORING) ? RAW_SCORING : `https://${RAW_SCORING}`;

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
      { source: "/api/incidents/simulate-nearmiss", destination: `${SCORING_SERVICE}/incidents/simulate-nearmiss` },
      { source: "/api/incidents/trace", destination: `${SCORING_SERVICE}/incidents/trace` },
      { source: "/api/incidents/clear", destination: `${SCORING_SERVICE}/incidents/clear` },
      { source: "/api/incidents/cv-detected", destination: `${SCORING_SERVICE}/incidents/cv-detected` },
      { source: "/api/training-stats", destination: `${SCORING_SERVICE}/training-stats` },
    ];
  },
};

export default nextConfig;
