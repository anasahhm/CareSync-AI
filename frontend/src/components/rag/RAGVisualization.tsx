"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search, BookOpen, Quote, Layers, Loader2 } from "lucide-react";
import { ragApi } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { RAGLoadingSkeleton } from "@/components/common/Skeleton";
import { useNotifications } from "@/providers/NotificationProvider";

interface RetrievalHit {
  text: string;
  source?: string;
  topic?: string;
  hybrid_score?: number;
  score?: number;
  title?: string;
  citation?: string;
  pubdate?: string;
}

interface EvidenceBundle {
  claim: string;
  guideline_hits: RetrievalHit[];
  pubmed_hits: RetrievalHit[];
  citations: string[];
  has_evidence: boolean;
}

function ScoreBar({ score, label }: { score: number; label: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-white/40 w-16 flex-shrink-0">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-white/8 overflow-hidden">
        <div className="h-full bg-gradient-to-r from-purple-500 to-teal-400" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-white/50 w-8 text-right flex-shrink-0">{pct}%</span>
    </div>
  );
}

function RAGVisualizationInner() {
  const [query, setQuery] = useState("");
  const { notify } = useNotifications();

  const mutation = useMutation({
    mutationFn: async (searchQuery: string) => {
      const { data } = await ragApi.search(searchQuery, 5);
      return data as EvidenceBundle;
    },
    onError: () => {
      notify({ type: "error", title: "Retrieval failed", message: "Could not reach the RAG service." });
    },
  });

  const handleSearch = () => {
    if (!query.trim()) return;
    mutation.mutate(query.trim());
  };

  return (
    <Card variant="glass" padding="md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Layers className="w-4 h-4" />
          RAG Retrieval Explorer
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="e.g. acute coronary syndrome chest pain"
            className="flex-1"
          />
          <Button size="sm" onClick={handleSearch} disabled={mutation.isPending || !query.trim()}>
            {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          </Button>
        </div>

        {mutation.isPending && <RAGLoadingSkeleton rows={2} />}

        {mutation.data && (
          <div className="space-y-3">
            {!mutation.data.has_evidence && (
              <p className="text-white/40 text-sm">No evidence found for this query.</p>
            )}

            {mutation.data.guideline_hits.map((hit, i) => (
              <div key={`g-${i}`} className="rounded-xl border border-white/8 bg-white/[0.02] p-3 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-xs text-white/60">
                    <BookOpen className="w-3 h-3" /> {hit.source || "Guideline"}
                  </span>
                  <Badge variant="outline" size="sm">hybrid rank</Badge>
                </div>
                <p className="text-sm text-white/75 leading-snug">{hit.text}</p>
                {typeof hit.hybrid_score === "number" && (
                  <ScoreBar score={hit.hybrid_score} label="Hybrid" />
                )}
              </div>
            ))}

            {mutation.data.pubmed_hits.map((hit, i) => (
              <div key={`p-${i}`} className="rounded-xl border border-white/8 bg-white/[0.02] p-3 space-y-1.5">
                <span className="flex items-center gap-1.5 text-xs text-white/60">
                  <BookOpen className="w-3 h-3" /> PubMed{hit.pubdate ? ` · ${hit.pubdate}` : ""}
                </span>
                <p className="text-sm text-white/75 leading-snug">{hit.title}</p>
              </div>
            ))}

            {mutation.data.citations.length > 0 && (
              <div className="pt-1 border-t border-white/8">
                <p className="text-[11px] uppercase tracking-wider text-white/30 mb-1.5 flex items-center gap-1">
                  <Quote className="w-3 h-3" /> Citations
                </p>
                <div className="flex flex-col gap-1">
                  {mutation.data.citations.map((c, i) => (
                    <p key={i} className="text-[11px] text-white/40 leading-snug">{c}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function RAGVisualization() {
  return (
    <ErrorBoundary section="RAG visualization">
      <RAGVisualizationInner />
    </ErrorBoundary>
  );
}
