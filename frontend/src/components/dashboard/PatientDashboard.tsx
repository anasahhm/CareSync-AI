"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Video, FileText, Plus, Activity, Clock,
  HeartPulse, Loader2, ChevronRight, AlertCircle
} from "lucide-react";
import { consultationApi, reportApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Textarea } from "@/components/ui/Input";
import { ReportViewer } from "@/components/consultation/ReportViewer";
import {
  formatDateTime, formatSeconds,
  consultationStatusLabel, consultationStatusColor
} from "@/lib/utils";
import type { Consultation, AIReport } from "@/types";

const ctaBtn =
  "bg-transparent hover:bg-blue-500 text-blue-400 hover:text-[#04070d] " +
  "border border-blue-500/50 hover:border-blue-500 rounded-md shadow-none " +
  "font-mono text-xs uppercase tracking-widest";

const mutedBtn =
  "bg-transparent hover:bg-white/90 text-white/60 hover:text-[#060608] " +
  "border border-white/15 hover:border-white/90 rounded-md shadow-none " +
  "font-mono text-xs uppercase tracking-widest";

export function PatientDashboard() {
  const { user } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showNewConsult, setShowNewConsult] = useState(false);
  const [complaint, setComplaint] = useState("");
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  const { data: consultations = [], isLoading: loadingConsults } = useQuery<Consultation[]>({
    queryKey: ["my-consultations"],
    queryFn: async () => {
      const { data } = await consultationApi.list();
      return data;
    },
  });

  const { data: reports = [] } = useQuery<AIReport[]>({
    queryKey: ["my-reports"],
    queryFn: async () => {
      const { data } = await reportApi.list();
      return Array.isArray(data) ? data : [];
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const { data } = await consultationApi.create({ chief_complaint: complaint || undefined });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["my-consultations"] });
      setShowNewConsult(false);
      setComplaint("");
      router.push(`/consultation/${data.room_id}`);
    },
  });

  const stats = [
    {
      label: "Total Consultations",
      value: consultations.length,
      icon: Video,
    },
    {
      label: "Completed",
      value: consultations.filter((c) => c.status === "COMPLETED").length,
      icon: Activity,
    },
    {
      label: "AI Reports",
      value: reports.filter((r) => r.status === "COMPLETED").length,
      icon: FileText,
    },
  ];

  return (
    <div className="flex flex-col gap-10 max-w-5xl mx-auto w-full">
      {/* ── Welcome Header ──────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6">
        <div>
          <p className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-3">
            Patient Dashboard
          </p>
          <h1 className="font-display italic text-3xl md:text-4xl font-normal text-white/95">
            Hello, {user?.full_name?.split(" ")[0]}
          </h1>
        </div>
        <Button
          leftIcon={<Plus className="w-3.5 h-3.5" />}
          onClick={() => setShowNewConsult(true)}
          className={ctaBtn}
        >
          New Consultation
        </Button>
      </div>

      {/* ── Stats Strip ──────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-6 pt-8 border-t border-white/5">
        {stats.map(({ label, value, icon: Icon }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="flex items-center gap-3"
          >
            <div className="w-9 h-9 rounded-[4px] flex items-center justify-center flex-shrink-0 bg-blue-500/8 border border-blue-500/20">
              <Icon className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-light text-white/90 font-mono leading-none">{value}</p>
              <p className="text-[11px] text-white/35 mt-1">{label}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* ── Main Grid ────────────────────────────────────────────── */}
      <div className="grid md:grid-cols-5 gap-8">
        {/* Consultations list */}
        <div className="md:col-span-3 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-mono text-white/30 uppercase tracking-widest">
              Recent Consultations
            </p>
            {loadingConsults && <Loader2 className="w-4 h-4 text-white/30 animate-spin" />}
          </div>

          {consultations.length === 0 && !loadingConsults ? (
            <Card variant="bordered" padding="lg" className="rounded-[4px] border-white/8">
              <div className="flex flex-col items-center gap-3 py-4">
                <Video className="w-8 h-8 text-white/15" />
                <p className="text-sm text-white/30 text-center">
                  No consultations yet. Start one to connect with a doctor.
                </p>
                <Button size="sm" onClick={() => setShowNewConsult(true)} className={ctaBtn}>
                  Start First Consultation
                </Button>
              </div>
            </Card>
          ) : (
            <div className="flex flex-col gap-3">
              {consultations.slice(0, 8).map((c, i) => (
                <motion.div
                  key={c.id}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <Card
                    variant="elevated"
                    padding="md"
                    className="rounded-[4px] bg-white/[0.02] border-white/8 hover:border-white/20 shadow-none cursor-pointer transition-all group"
                    onClick={() => {
                      if (c.status === "WAITING" || c.status === "ACTIVE") {
                        router.push(`/consultation/${c.room_id}`);
                      }
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="w-8 h-8 rounded-[4px] bg-blue-500/8 border border-blue-500/20 flex items-center justify-center flex-shrink-0">
                          <HeartPulse className="w-4 h-4 text-blue-400" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm text-white/80 truncate">
                            {c.chief_complaint || "General consultation"}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <Clock className="w-3 h-3 text-white/25" />
                            <span className="text-xs font-mono text-white/30">
                              {formatDateTime(c.created_at)}
                            </span>
                            {c.duration_seconds && (
                              <span className="text-xs font-mono text-white/25">
                                · {formatSeconds(c.duration_seconds)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Badge
                          className={`${consultationStatusColor(c.status)} font-mono uppercase tracking-wide rounded-[3px]`}
                          variant="outline"
                          dot
                          size="sm"
                        >
                          {consultationStatusLabel(c.status)}
                        </Badge>
                        {(c.status === "WAITING" || c.status === "ACTIVE") && (
                          <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-white/50 transition-colors" />
                        )}
                      </div>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Reports sidebar */}
        <div className="md:col-span-2 flex flex-col gap-4">
          <p className="text-[11px] font-mono text-white/30 uppercase tracking-widest">AI Reports</p>
          {reports.length === 0 ? (
            <Card variant="bordered" padding="md" className="rounded-[4px] border-white/8">
              <div className="flex flex-col items-center gap-2 py-3">
                <FileText className="w-6 h-6 text-white/15" />
                <p className="text-xs text-white/30 text-center">Reports appear after consultations</p>
              </div>
            </Card>
          ) : (
            <div className="flex flex-col gap-2">
              {reports.slice(0, 6).map((r) => (
                <button
                  key={r.id}
                  onClick={() => setSelectedReportId(r.consultation_id)}
                  className="flex items-center gap-3 p-3 rounded-[4px] border border-white/8 hover:border-white/20 bg-white/[0.02] text-left transition-all group"
                >
                  <div className="w-7 h-7 rounded-[4px] bg-purple-500/8 border border-purple-500/20 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-3.5 h-3.5 text-purple-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-white/70 truncate">
                      {r.summary?.slice(0, 40) ?? "Consultation report"}...
                    </p>
                    <p className="text-[10px] font-mono text-white/25 mt-0.5">
                      {r.generated_at ? formatDateTime(r.generated_at) : "Pending"}
                    </p>
                  </div>
                  <Badge
                    variant={r.status === "COMPLETED" ? "success" : r.status === "GENERATING" ? "warning" : "default"}
                    size="sm"
                    className="font-mono uppercase tracking-wide rounded-[3px]"
                  >
                    {r.status}
                  </Badge>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* New Consultation Modal */}
      <Modal
        open={showNewConsult}
        onClose={() => setShowNewConsult(false)}
        title="New Consultation"
        description="Describe your symptoms briefly so the doctor is prepared."
      >
        <div className="flex flex-col gap-4">
          <Textarea
            label="Chief Complaint (optional)"
            placeholder="e.g. Persistent headache and mild fever for 2 days..."
            value={complaint}
            onChange={(e) => setComplaint(e.target.value)}
            rows={4}
          />
          <div className="flex gap-3">
            <Button fullWidth onClick={() => setShowNewConsult(false)} className={mutedBtn}>
              Cancel
            </Button>
            <Button
              fullWidth
              loading={createMutation.isPending}
              onClick={() => createMutation.mutate()}
              className={ctaBtn}
            >
              Start Session
            </Button>
          </div>
          {createMutation.isError && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" />
              Failed to create consultation. Please try again.
            </p>
          )}
        </div>
      </Modal>

      {/* Report Viewer Modal */}
      <Modal
        open={!!selectedReportId}
        onClose={() => setSelectedReportId(null)}
        title="Consultation Report"
        size="lg"
      >
        {selectedReportId && <ReportViewer consultationId={selectedReportId} />}
      </Modal>
    </div>
  );
}