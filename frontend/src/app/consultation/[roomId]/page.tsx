"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, AlertCircle } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { consultationApi } from "@/lib/api";
import ConsultationRoom from "@/components/consultation/ConsultationRoom";
import type { Consultation } from "@/types";

export default function ConsultationRoomPage() {
  const params = useParams();
  const router = useRouter();
  const { isAuthenticated, hasHydrated, user } = useAuthStore();
  const roomId = params.roomId as string;

  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.replace(`/auth/login?redirect=/consultation/${roomId}`);
      return;
    }

    async function init() {
      try {
        // Find consultation by room_id — search in user's consultations
        const { data: consultations } = await consultationApi.list();
        const found = (consultations as Consultation[]).find(
          (c: Consultation) => c.room_id === roomId
        );

        if (!found) {
          // Doctor joining a new consultation — join it first
          if (user?.role === "DOCTOR") {
            // We need the consultation ID — get from waiting queue context
            // For now, show an error asking them to join from dashboard
            setError("Please join this consultation from your dashboard.");
            return;
          }
          setError("Consultation not found.");
          return;
        }

        // Doctor auto-joins if not yet assigned
        if (user?.role === "DOCTOR" && found.status === "WAITING") {
          await consultationApi.join(found.id);
          setConsultation({ ...found, status: "ACTIVE", room_id: roomId });
        } else {
          setConsultation(found);
        }
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          "Failed to load consultation";
        setError(msg);
      } finally {
        setLoading(false);
      }
    }

    init();
  }, [hasHydrated, isAuthenticated, roomId, router, user]);

  if (!hasHydrated || loading) {
    return (
      <div className="min-h-screen bg-[#060608] flex flex-col items-center justify-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
          <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
        </div>
        <p className="text-white/30 text-sm font-mono">Connecting to session…</p>
      </div>
    );
  }

  if (error || !consultation) {
    return (
      <div className="min-h-screen bg-[#060608] flex flex-col items-center justify-center gap-4 p-6">
        <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
          <AlertCircle className="w-5 h-5 text-red-400" />
        </div>
        <div className="text-center">
          <p className="text-white/70 text-sm mb-1">{error ?? "Consultation not found"}</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="text-xs text-blue-400 hover:text-blue-300 underline transition-colors"
          >
            Return to dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <ConsultationRoom
      consultationId={consultation.id}
      roomId={roomId}
    />
  );
}
