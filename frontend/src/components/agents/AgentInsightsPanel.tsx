"use client";

import { Suspense, lazy, useState } from "react";
import { Clock, Brain, Layers } from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentTimelineSkeleton, MemoryLoadingSkeleton, RAGLoadingSkeleton } from "@/components/common/Skeleton";

// Lazy-loaded so switching tabs doesn't pay the cost of all three panels'
// code (and their query hooks firing) until a tab is actually opened.
const ConsensusTimeline = lazy(() =>
  import("@/components/agents/ConsensusTimeline").then((m) => ({ default: m.ConsensusTimeline }))
);
const MemoryVisualization = lazy(() =>
  import("@/components/memory/MemoryVisualization").then((m) => ({ default: m.MemoryVisualization }))
);
const RAGVisualization = lazy(() =>
  import("@/components/rag/RAGVisualization").then((m) => ({ default: m.RAGVisualization }))
);

type InsightsTab = "timeline" | "memory" | "rag";

const TABS: { id: InsightsTab; label: string; icon: typeof Clock }[] = [
  { id: "timeline", label: "Consensus Timeline", icon: Clock },
  { id: "memory", label: "Memory", icon: Brain },
  { id: "rag", label: "RAG Explorer", icon: Layers },
];

interface AgentInsightsPanelProps {
  consultationId: string;
  patientId?: string;
  /** Only doctors should see internal agent/memory/RAG debugging views */
  visible?: boolean;
}

export function AgentInsightsPanel({ consultationId, patientId, visible = true }: AgentInsightsPanelProps) {
  const [activeTab, setActiveTab] = useState<InsightsTab>("timeline");

  if (!visible) return null;
  if (!consultationId) {
    return (
      <div className="rounded-xl border border-white/8 bg-white/[0.02] p-6 text-center text-sm text-white/40">
        No consultation selected yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-1 rounded-xl border border-white/8 bg-white/[0.02] p-1 w-fit">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                active ? "bg-white/10 text-white" : "text-white/40 hover:text-white/70"
              )}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="min-h-[240px]">
        {activeTab === "timeline" && (
          <Suspense fallback={<AgentTimelineSkeleton />}>
            <ConsensusTimeline consultationId={consultationId} />
          </Suspense>
        )}

        {activeTab === "memory" && (
          <Suspense fallback={<MemoryLoadingSkeleton />}>
            <MemoryVisualization consultationId={consultationId} patientId={patientId} />
          </Suspense>
        )}

        {activeTab === "rag" && (
          <Suspense fallback={<RAGLoadingSkeleton />}>
            <RAGVisualization />
          </Suspense>
        )}
      </div>
    </div>
  );
}
