"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText, AlertTriangle, CheckCircle2, Clock,
  Activity, ChevronRight, Loader2, MapPin,
  Download, FileJson, FileCode
} from "lucide-react";
import { reportApi, reportExportUrl } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatDateTime } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import { AgentInsightsPanel } from "@/components/agents/AgentInsightsPanel";
import type { AIReport } from "@/types";

type ExportFormat = "pdf" | "markdown" | "json";

interface ExportToast {
  type: "success" | "error";
  message: string;
}

interface ReportViewerProps {
  consultationId: string;
}

export function ReportViewer({ consultationId }: ReportViewerProps) {
  const { accessToken, user } = useAuthStore();
  const isDoctor = user?.role === "DOCTOR";
  const [exporting, setExporting] = useState<ExportFormat | null>(null);
  const [toast, setToast] = useState<ExportToast | null>(null);

  const showToast = (t: ExportToast) => {
    setToast(t);
    setTimeout(() => setToast(null), 3500);
  };

  const handleExport = async (format: ExportFormat) => {
    setExporting(format);
    try {
      const response = await fetch(reportExportUrl(consultationId, format), {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
      });
      if (!response.ok) throw new Error(`Export failed (${response.status})`);

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const extension = format === "markdown" ? "md" : format;
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${consultationId}.${extension}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      showToast({ type: "success", message: `Report exported as ${format.toUpperCase()}` });
    } catch {
      showToast({ type: "error", message: `Could not export as ${format.toUpperCase()}` });
    } finally {
      setExporting(null);
    }
  };

  const { data: report, isLoading, isError, refetch } = useQuery<AIReport>({
    queryKey: ["report", consultationId],
    queryFn: async () => {
      const { data } = await reportApi.get(consultationId);
      return data;
    },
    refetchInterval: (query) => {
      // Poll every 3s while generating
      if (query.state.data?.status === "GENERATING") return 3000;
      return false;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 gap-3">
        <Loader2 className="w-5 h-5 text-white/30 animate-spin" />
        <span className="text-white/40 text-sm">Loading report...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <FileText className="w-8 h-8 text-white/20" />
        <p className="text-white/40 text-sm">Report not found</p>
        <button
          onClick={() => refetch()}
          className="text-xs text-blue-400 hover:text-blue-300 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!report) return null;

  if (report.status === "GENERATING" || report.status === "PENDING") {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <div className="relative w-12 h-12">
          <Loader2 className="w-12 h-12 text-purple-500/30 animate-spin" />
          <Activity className="w-5 h-5 text-purple-400 absolute inset-0 m-auto" />
        </div>
        <div className="text-center">
          <p className="text-white/70 text-sm font-medium">AI is generating your report</p>
          <p className="text-white/30 text-xs mt-1">This usually takes 15–30 seconds</p>
        </div>
      </div>
    );
  }

  if (report.status === "FAILED") {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <AlertTriangle className="w-8 h-8 text-amber-400/50" />
        <p className="text-white/50 text-sm">Report generation failed</p>
      </div>
    );
  }

  const sections = [
    {
      icon: Activity,
      title: "Summary",
      color: "blue",
      content: report.summary && (
        <p className="text-sm text-white/70 leading-relaxed">{report.summary}</p>
      ),
    },
    {
      icon: AlertTriangle,
      title: "Symptoms Observed",
      color: "amber",
      content: report.symptoms_observed?.length ? (
        <ul className="flex flex-col gap-1.5">
          {report.symptoms_observed.map((s, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-white/70">
              <ChevronRight className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
              {s}
            </li>
          ))}
        </ul>
      ) : null,
    },
    {
      icon: MapPin,
      title: "Areas Marked",
      color: "red",
      content: report.areas_marked?.length ? (
        <div className="flex flex-wrap gap-2">
          {report.areas_marked.map((a, i) => (
            <Badge key={i} variant="danger" size="sm">{a}</Badge>
          ))}
        </div>
      ) : null,
    },
    {
      icon: CheckCircle2,
      title: "Suggested Next Steps",
      color: "teal",
      content: report.suggested_next_steps?.length ? (
        <ul className="flex flex-col gap-1.5">
          {report.suggested_next_steps.map((s, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-white/70">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
              {s}
            </li>
          ))}
        </ul>
      ) : null,
    },
    {
      icon: AlertTriangle,
      title: "Risk Indicators",
      color: "red",
      content: report.risk_indicators?.length ? (
        <ul className="flex flex-col gap-1.5">
          {report.risk_indicators.map((r, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-amber-300/80">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
              {r}
            </li>
          ))}
        </ul>
      ) : null,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full max-h-[85vh] overflow-y-auto rounded-2xl border border-white/8 bg-[#0a0a0f] p-4 flex flex-col gap-4"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-purple-500/15 border border-purple-500/25 flex items-center justify-center flex-shrink-0">
            <FileText className="w-4 h-4 text-purple-400" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-white/90 truncate">AI Consultation Report</h3>
            {report.generated_at && (
              <p className="text-xs text-white/30 flex items-center gap-1 mt-0.5">
                <Clock className="w-3 h-3" />
                {formatDateTime(report.generated_at)}
              </p>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={exporting !== null}
            onClick={() => handleExport("pdf")}
          >
            {exporting === "pdf" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
            <span className="ml-1.5">PDF</span>
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={exporting !== null}
            onClick={() => handleExport("markdown")}
          >
            {exporting === "markdown" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileCode className="w-3.5 h-3.5" />}
            <span className="ml-1.5">Markdown</span>
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={exporting !== null}
            onClick={() => handleExport("json")}
          >
            {exporting === "json" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileJson className="w-3.5 h-3.5" />}
            <span className="ml-1.5">JSON</span>
          </Button>
          <Badge variant="success" dot>Complete</Badge>
        </div>
      </div>

      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs border ${
              toast.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/25 text-emerald-300"
                : "bg-red-500/10 border-red-500/25 text-red-300"
            }`}
          >
            {toast.type === "success" ? (
              <CheckCircle2 className="w-3.5 h-3.5" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5" />
            )}
            {toast.message}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-start">
        {sections.map(({ icon: Icon, title, content }) =>
          content ? (
            <Card key={title} variant="elevated" padding="md">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Icon className="w-3.5 h-3.5 text-white/40" />
                  <CardTitle className="text-xs uppercase tracking-wider text-white/40 font-mono">
                    {title}
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>{content}</CardContent>
            </Card>
          ) : null
        )}
      </div>

      {/* Disclaimer */}
      <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400/70 flex-shrink-0 mt-0.5" />
        <p className="text-[11px] text-amber-300/60 leading-relaxed">
          {report.structured_data?.ai_disclaimer ??
            "AI-generated assistance only. Not a final medical diagnosis. Consult your healthcare provider for medical advice."}
        </p>
      </div>

      {isDoctor && (
        <div className="pt-2 border-t border-white/8">
          <p className="text-[11px] uppercase tracking-wider text-white/30 mb-3">Agent Insights (Doctor View)</p>
          <AgentInsightsPanel consultationId={consultationId} />
        </div>
      )}
    </motion.div>
  );
}