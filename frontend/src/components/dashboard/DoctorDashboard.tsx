"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Users, Video, FileText, Clock,
  Loader2, Stethoscope, CheckCircle2,
  UserCheck, BrainCircuit
} from "lucide-react";
import { api, consultationApi, reportApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Avatar } from "@/components/ui/Avatar";
import { Modal } from "@/components/ui/Modal";
import { ReportViewer } from "@/components/consultation/ReportViewer";
import { GPUDashboard } from "@/components/gpu/GPUDashboard";
import {
  formatDateTime, formatSeconds,
  consultationStatusLabel, consultationStatusColor
} from "@/lib/utils";
import type { Consultation, AIReport } from "@/types";

const joinBtn =
  "bg-transparent hover:bg-emerald-500 text-emerald-400 hover:text-[#04070d] " +
  "border border-emerald-500/50 hover:border-emerald-500 rounded-md shadow-none " +
  "font-mono text-[11px] uppercase tracking-widest";

export function DoctorDashboard() {
  const { user } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  // My consultations
  const { data: myConsultations = [], isLoading: loadingMine } = useQuery<Consultation[]>({
    queryKey: ["doctor-consultations"],
    queryFn: async () => {
      const { data } = await consultationApi.list();
      return data;
    },
    refetchInterval: 30_000,
  });

  // Waiting queue (patients without a doctor)
  const { data: waitingQueue = [], isLoading: loadingQueue } = useQuery<Consultation[]>({
    queryKey: ["waiting-queue"],
    queryFn: async () => {
      const { data } = await api.get("/consultations/waiting");
      return data;
    },
    refetchInterval: 10_000,
  });

  // My reports
  const { data: reports = [] } = useQuery<AIReport[]>({
    queryKey: ["doctor-reports"],
    queryFn: async () => {
      const { data } = await reportApi.list();
      return Array.isArray(data) ? data : [];
    },
  });

  const joinMutation = useMutation({
    mutationFn: async (consultationId: string) => {
      const { data } = await consultationApi.join(consultationId);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["waiting-queue"] });
      router.push(`/consultation/${data.room_id}`);
    },
  });

  const stats = [
    {
      label: "Waiting",
      value: waitingQueue.length,
      icon: Users,
      color: "amber",
      urgent: waitingQueue.length > 0,
    },
    {
      label: "My Active",
      value: myConsultations.filter((c) => c.status === "ACTIVE").length,
      icon: Video,
      color: "green",
      urgent: false,
    },
    {
      label: "Completed Today",
      value: myConsultations.filter((c) => {
        if (c.status !== "COMPLETED" || !c.ended_at) return false;
        const today = new Date().toDateString();
        return new Date(c.ended_at).toDateString() === today;
      }).length,
      icon: CheckCircle2,
      color: "blue",
      urgent: false,
    },
    {
      label: "AI Reports",
      value: reports.filter((r) => r.status === "COMPLETED").length,
      icon: BrainCircuit,
      color: "purple",
      urgent: false,
    },
  ];

  const iconBoxColor: Record<string, string> = {
    amber: "bg-amber-500/8 border-amber-500/20",
    green: "bg-emerald-500/8 border-emerald-500/20",
    blue: "bg-blue-500/8 border-blue-500/20",
    purple: "bg-purple-500/8 border-purple-500/20",
  };
  const iconTextColor: Record<string, string> = {
    amber: "text-amber-400",
    green: "text-emerald-400",
    blue: "text-blue-400",
    purple: "text-purple-400",
  };

  return (
    <div className="flex flex-col gap-10 max-w-6xl mx-auto w-full">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6">
        <div>
          <p className="text-[11px] font-mono text-white/30 uppercase tracking-widest mb-3">
            Doctor Dashboard
          </p>
          <h1 className="font-display italic text-3xl md:text-4xl font-normal text-white/95">
            Dr. {user?.full_name?.split(" ").slice(-1)[0]}
          </h1>
        </div>
        {waitingQueue.length > 0 && (
          <Badge variant="warning" dot className="animate-pulse font-mono uppercase tracking-widest rounded-[3px]">
            {waitingQueue.length} patient{waitingQueue.length > 1 ? "s" : ""} waiting
          </Badge>
        )}
      </div>

      {/* ── Stats Strip ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-8 border-t border-white/5">
        {stats.map(({ label, value, icon: Icon, color, urgent }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="flex items-center gap-3"
          >
            <div className={`w-9 h-9 rounded-[4px] flex items-center justify-center flex-shrink-0 border ${iconBoxColor[color]}`}>
              <Icon className={`w-4 h-4 ${iconTextColor[color]}`} />
            </div>
            <div>
              <p className={`text-2xl font-light font-mono leading-none ${urgent ? "text-amber-400" : "text-white/90"}`}>
                {value}
              </p>
              <p className="text-[11px] text-white/35 mt-1">{label}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* ── Main Grid ────────────────────────────────────────────── */}
      <div className="grid md:grid-cols-5 gap-8">
        {/* Left: Queue + My Consultations */}
        <div className="md:col-span-3 flex flex-col gap-8">
          {/* Patient Queue */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-mono text-white/30 uppercase tracking-widest flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                Patient Queue
              </p>
              {loadingQueue && <Loader2 className="w-4 h-4 text-white/30 animate-spin" />}
            </div>

            {waitingQueue.length === 0 ? (
              <Card variant="bordered" padding="md" className="rounded-[4px] border-white/8">
                <div className="flex items-center gap-3 py-2">
                  <UserCheck className="w-5 h-5 text-emerald-400/40" />
                  <p className="text-sm text-white/30">No patients waiting</p>
                </div>
              </Card>
            ) : (
              <div className="flex flex-col gap-2">
                {waitingQueue.map((c, i) => (
                  <motion.div
                    key={c.id}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <Card variant="elevated" padding="md" className="rounded-[4px] bg-white/[0.02] border-amber-500/10 hover:border-amber-500/30 shadow-none transition-all">
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <Avatar name="Patient" role="PATIENT" size="sm" />
                          <div className="min-w-0">
                            <p className="text-sm text-white/80 truncate">
                              {c.chief_complaint || "General consultation"}
                            </p>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <Clock className="w-3 h-3 text-white/25" />
                              <span className="text-xs font-mono text-white/30">{formatDateTime(c.created_at)}</span>
                            </div>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          loading={joinMutation.isPending}
                          leftIcon={<Video className="w-3.5 h-3.5" />}
                          onClick={() => joinMutation.mutate(c.id)}
                          className={joinBtn}
                        >
                          Join
                        </Button>
                      </div>
                    </Card>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* My Past Consultations */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-mono text-white/30 uppercase tracking-widest">My Consultations</p>
              {loadingMine && <Loader2 className="w-4 h-4 text-white/30 animate-spin" />}
            </div>
            <div className="flex flex-col gap-2">
              {myConsultations.slice(0, 6).map((c, i) => (
                <motion.div
                  key={c.id}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 + i * 0.05 }}
                >
                  <Card
                    variant="elevated"
                    padding="md"
                    className={`rounded-[4px] bg-white/[0.02] shadow-none cursor-pointer hover:border-white/20 transition-all group
                      ${c.status === "ACTIVE" ? "border-emerald-500/25" : "border-white/8"}`}
                    onClick={() => {
                      if (c.status === "ACTIVE") router.push(`/consultation/${c.room_id}`);
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="w-7 h-7 rounded-[4px] bg-teal-500/8 border border-teal-500/20 flex items-center justify-center flex-shrink-0">
                          <Stethoscope className="w-3.5 h-3.5 text-teal-400" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm text-white/80 truncate">
                            {c.chief_complaint || "General consultation"}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs font-mono text-white/30">{formatDateTime(c.created_at)}</span>
                            {c.duration_seconds && (
                              <span className="text-xs font-mono text-white/25">· {formatSeconds(c.duration_seconds)}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <Badge
                        className={`${consultationStatusColor(c.status)} font-mono uppercase tracking-wide rounded-[3px]`}
                        variant="outline"
                        dot
                        size="sm"
                      >
                        {consultationStatusLabel(c.status)}
                      </Badge>
                    </div>
                  </Card>
                </motion.div>
              ))}
              {myConsultations.length === 0 && !loadingMine && (
                <Card variant="bordered" padding="md" className="rounded-[4px] border-white/8">
                  <p className="text-sm text-white/30 text-center py-2">No consultations yet</p>
                </Card>
              )}
            </div>
          </div>
        </div>

        {/* Right: GPU status + AI Reports */}
        <div className="md:col-span-2 flex flex-col gap-4">
          <GPUDashboard />
          <p className="text-[11px] font-mono text-white/30 uppercase tracking-widest">AI Reports</p>
          {reports.length === 0 ? (
            <Card variant="bordered" padding="md" className="rounded-[4px] border-white/8">
              <div className="flex flex-col items-center gap-2 py-4">
                <BrainCircuit className="w-6 h-6 text-white/15" />
                <p className="text-xs text-white/30 text-center">Reports generated after consultations</p>
              </div>
            </Card>
          ) : (
            <div className="flex flex-col gap-2">
              {reports.slice(0, 8).map((r) => (
                <button
                  key={r.id}
                  onClick={() => setSelectedReportId(r.consultation_id)}
                  className="flex items-center gap-3 p-3 rounded-[4px] border border-white/8 hover:border-white/20 bg-white/[0.02] text-left transition-all"
                >
                  <div className="w-7 h-7 rounded-[4px] bg-purple-500/8 border border-purple-500/20 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-3.5 h-3.5 text-purple-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-white/70 truncate">
                      {r.summary?.slice(0, 35) ?? "Report"}...
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
                    {r.status === "COMPLETED" ? "Done" : r.status}
                  </Badge>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Report Modal */}
      <Modal
        open={!!selectedReportId}
        onClose={() => setSelectedReportId(null)}
        title="AI Consultation Report"
        size="lg"
      >
        {selectedReportId && <ReportViewer consultationId={selectedReportId} />}
      </Modal>
    </div>
  );
}