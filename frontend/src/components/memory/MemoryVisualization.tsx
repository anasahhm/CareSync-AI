"use client";

import { useQuery } from "@tanstack/react-query";
import { Brain, MessageSquare, Share2, History, Database } from "lucide-react";
import { memoryApi } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { MemoryLoadingSkeleton } from "@/components/common/Skeleton";
import { formatDateTime } from "@/lib/utils";

interface ConsultationMemoryResponse {
  consultation_id: string;
  turns: { speaker: string; text: string }[];
  agent_outputs: Record<string, { status: string; confidence: number; recommendation_count: number; escalation_count: number }>;
  shared_facts: Record<string, unknown>;
}

interface PatientMemoryResponse {
  patient_id: string;
  history: { consultation_id: string; created_at: string | null; chief_complaint: string | null; risk_score: number | null }[];
  similar_visits: { entry_id: string; score: number; text: string }[];
  semantic_backend: string;
}

interface MemoryVisualizationProps {
  consultationId: string;
  patientId?: string;
}

function MemoryVisualizationInner({ consultationId, patientId }: MemoryVisualizationProps) {
  const { data: consultMemory, isLoading: consultLoading } = useQuery<ConsultationMemoryResponse>({
    queryKey: ["memory-consultation", consultationId],
    queryFn: async () => {
      const { data } = await memoryApi.consultation(consultationId);
      return data;
    },
    refetchInterval: 5000,
  });

  const { data: patientMemory, isLoading: patientLoading } = useQuery<PatientMemoryResponse>({
    queryKey: ["memory-patient", patientId],
    queryFn: async () => {
      const { data } = await memoryApi.patient(patientId as string);
      return data;
    },
    enabled: !!patientId,
  });

  if (consultLoading) {
    return <MemoryLoadingSkeleton />;
  }

  const agentOutputEntries = Object.entries(consultMemory?.agent_outputs ?? {});
  const sharedFactEntries = Object.entries(consultMemory?.shared_facts ?? {});

  return (
    <div className="space-y-4">
      <Card variant="glass" padding="md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="w-4 h-4" />
            Consultation Memory
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-white/30 mb-2 flex items-center gap-1">
              <MessageSquare className="w-3 h-3" /> Conversation ({consultMemory?.turns.length ?? 0} turns)
            </p>
            {(consultMemory?.turns.length ?? 0) === 0 ? (
              <p className="text-white/40 text-sm">No conversation turns recorded yet.</p>
            ) : (
              <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                {consultMemory!.turns.slice(-10).map((turn, i) => (
                  <div key={i} className="text-xs">
                    <span className="text-white/40 font-mono">{turn.speaker}:</span>{" "}
                    <span className="text-white/70">{turn.text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="text-[11px] uppercase tracking-wider text-white/30 mb-2 flex items-center gap-1">
              <Database className="w-3 h-3" /> Agent Outputs Recorded ({agentOutputEntries.length})
            </p>
            {agentOutputEntries.length === 0 ? (
              <p className="text-white/40 text-sm">No agent outputs recorded yet.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {agentOutputEntries.map(([agentType, output]) => (
                  <Badge key={agentType} variant={output.status === "COMPLETED" ? "success" : "outline"} size="sm">
                    {agentType} · {output.recommendation_count} rec{output.escalation_count > 0 ? ` · ${output.escalation_count} esc` : ""}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="text-[11px] uppercase tracking-wider text-white/30 mb-2 flex items-center gap-1">
              <Share2 className="w-3 h-3" /> Shared Facts ({sharedFactEntries.length})
            </p>
            {sharedFactEntries.length === 0 ? (
              <p className="text-white/40 text-sm">No cross-agent facts shared yet.</p>
            ) : (
              <div className="space-y-1">
                {sharedFactEntries.map(([key, value]) => (
                  <div key={key} className="flex items-start gap-2 text-xs">
                    <span className="text-white/40 font-mono flex-shrink-0">{key}:</span>
                    <span className="text-white/70 truncate">{JSON.stringify(value)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {patientId && (
        <Card variant="glass" padding="md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <History className="w-4 h-4" />
              Patient Long-Term Memory
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {patientLoading ? (
              <MemoryLoadingSkeleton />
            ) : (
              <>
                <p className="text-[11px] text-white/30">
                  Semantic backend: <span className="text-white/50">{patientMemory?.semantic_backend}</span>
                </p>
                {(patientMemory?.history.length ?? 0) === 0 ? (
                  <p className="text-white/40 text-sm">No prior consultations on record.</p>
                ) : (
                  <div className="space-y-1.5">
                    {patientMemory!.history.map((h) => (
                      <div key={h.consultation_id} className="flex items-center justify-between text-xs border-b border-white/6 pb-1.5">
                        <span className="text-white/60">{h.chief_complaint || "Unspecified complaint"}</span>
                        <span className="text-white/30">{h.created_at ? formatDateTime(h.created_at) : ""}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export function MemoryVisualization(props: MemoryVisualizationProps) {
  return (
    <ErrorBoundary section="Memory visualization">
      <MemoryVisualizationInner {...props} />
    </ErrorBoundary>
  );
}
