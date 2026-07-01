import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "One Care — Morning Triage",
  description:
    "Decide-layer eldercare triage dashboard. Acute events preempt; chronic anomalies rank the calm caseload beneath. Deterministic rationale.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
