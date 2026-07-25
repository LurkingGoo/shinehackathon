import type { Metadata } from "next";
import { TrainingPanel } from "@/components/TrainingPanel";

export const metadata: Metadata = {
  title: "One Care | How the model was trained",
  description:
    "The judge-metrics page: the recorded training run of the illustrative magnitude classifier, real train/test splits, and why the shipped detector reads the temporal fall signature instead.",
};

export default function TrainingPage() {
  return <TrainingPanel />;
}
