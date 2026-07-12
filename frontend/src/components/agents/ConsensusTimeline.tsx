"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity, CheckCircle2, XCircle, Clock, Gavel,
  TrendingUp, AlertTriangle, Users
} from "lucide-react";
import { agentTimelineApi } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { AgentTimelineSkeleton } from "@/components/common/Skeleton";

interface TimelineEvent {
  event_type: string;
  source_agent: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

interface ConsensusData {
  primary_diagnosis: string | null;
  consensus_score: number;
  risk_level: string;
  agents_agreed: number;
  agents_total: number;
  final_recommendations: unknown[];
  status: string;
}

const EVENT_ICON: Record<string, typeof Activity> = {
  agent_started: Activity,
  agent_processing: Activity,
  agent_completed: CheckCircle2,
  agent_failed: XCircle,
  recommendation_available: TrendingUp,
  escalation_required: AlertTriangle,
  moderator_decision: Gavel,
  consensus_update: Users,
};

const EVENT_COLOR: Record<string, string> = {
  agent_started: "text-blue-400",
  agent_processing: "text-blue-400",
  agent_completed: "text-emerald-400",
  agent_failed: "text-red-400",
  recommendation_available: "text-purple-400",
  escalation_required: "text-amber-400",
  moderator_decision: "text-teal-400",
  consensus_update: "text-pink-400",
};

function formatEventLabel(event: TimelineEvent): string {
  const agent = (event.payload?.agent_type as string) || event.source_agent || "System";
  switch (event.event_type) {
    case "agent_started":
      return `${agent} started analyzing`;
    case "agent_processing":
      return `${agent} processing`;
    case "agent_completed":
      return `${agent} completed`;
    case "agent_failed":
      return `${agent} failed`;
    case "recommendation_available":
      return `${agent} published a recommendation`;
    case "escalation_required":
      return `${agent} raised an escalation`;
    case "moderator_decision":
      return "Consensus Moderator resolved conflicts";
    case "consensus_update":
      return "Consensus updated";
    default:
      return `${agent}: ${event.event_type}`;
  }
}

interface ConsensusTimelineProps {
  consultationId: string;
}

function ConsensusTimelineInner({ consultationId }: ConsensusTimelineProps) {
  const { data: timelineData, isLoading: timelineLoading } = useQuery<{ events: TimelineEvent[]; event_count: number }>({
    queryKey: ["agent-timeline", consultationId],
    queryFn: async () => {
      const { data } = await agentTimelineApi.timeline(consultationId);
      return data;
    },
    refetchInterval: 4000,
  });

  const { data: consensus } = useQuery<ConsensusData>({
    queryKey: ["consensus", consultationId],
    queryFn: async () => {
      const { data } = await agentTimelineApi.consensus(consultationId);
      return data;
    },
    retry: false,
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 4000 : false),
  });

  if (timelineLoading) {
    return <AgentTimelineSkeleton />;
  }

  const events = timelineData?.events ?? [];
  const completedCount = events.filter((e) => e.event_type === "agent_completed").length;
  const failedCount = events.filter((e) => e.event_type === "agent_failed").length;

  return (
    <div className="space-y-4">
      {consensus && consensus.status === "complete" && (
        <Card variant="glass" padding="md" glow="purple">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Gavel className="w-4 h-4" />
              Final Consensus
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {consensus.primary_diagnosis && (
              <p className="text-sm text-white/80">{consensus.primary_diagnosis}</p>
            )}
            <div className="flex items-center gap-3 flex-wrap">
              <Badge variant="success">
                {(consensus.consensus_score * 100).toFixed(0)}% consensus
              </Badge>
              <Badge variant={consensus.risk_level === "HIGH" || consensus.risk_level === "CRITICAL" ? "danger" : "outline"}>
                Risk: {consensus.risk_level}
              </Badge>
              <span className="text-xs text-white/40">
                {consensus.agents_agreed}/{consensus.agents_total} agents agreed
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      <Card variant="glass" padding="md">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Clock className="w-4 h-4" />
            Agent Execution Timeline
          </CardTitle>
          <div className="flex items-center gap-2 text-xs text-white/40">
            <span>{completedCount} completed</span>
            {failedCount > 0 && <span className="text-red-400">{failedCount} failed</span>}
          </div>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <p className="text-white/40 text-sm">No agent activity recorded yet.</p>
          ) : (
            <div className="space-y-1.5 max-h-96 overflow-y-auto pr-1">
              {events.map((event, i) => {
                const Icon = EVENT_ICON[event.event_type] || Activity;
                const color = EVENT_COLOR[event.event_type] || "text-white/40";
                return (
                  <div
                    key={`${event.timestamp}-${i}`}
                    className="flex items-center gap-3 rounded-lg border border-white/6 bg-white/[0.015] px-3 py-2"
                  >
                    <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${color}`} />
                    <span className="text-xs text-white/70 flex-1">{formatEventLabel(event)}</span>
                    <span className="text-[10px] text-white/25 font-mono">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function ConsensusTimeline(props: ConsensusTimelineProps) {
  return (
    <ErrorBoundary section="Consensus timeline">
      <ConsensusTimelineInner {...props} />
    </ErrorBoundary>
  );
}
