import type { Metadata } from "next";
import { HardwarePanel } from "@/components/HardwarePanel";

export const metadata: Metadata = {
  title: "One Care | Hardware Companion",
  description:
    "The sense layer showcase: Bangle.js 2 reference wearable, what we adapt on the stock device, and the live link into the triage dashboard.",
};

export default function HardwarePage() {
  return <HardwarePanel />;
}
