import type { Metadata } from "next";
import { WatchPanel } from "@/components/WatchPanel";

export const metadata: Metadata = {
  title: "One Care | Camera Watch",
  description:
    "In-browser pose fall detection: upright, horizontal within two seconds, three seconds of stillness — then the incident fires into the triage dashboard.",
};

export default function WatchPage() {
  return <WatchPanel />;
}
