/**
 * GestureMed AI — Consultation Room
 * Full WebRTC + Socket.IO + gesture + annotation telemedicine UI.
 */
"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mic, MicOff, Video, VideoOff, PhoneOff, Hand,
  Pencil, Trash2, FileText,
  Users, Clock, Activity
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useConsultationSocket, AnnotationEvent, GestureEvent } from "@/hooks/useConsultationSocket";
import { useWebRTC } from "@/hooks/useWebRTC";
import { useGestureCamera } from "@/hooks/useGestureCamera";
import { consultationApi, reportApi } from "@/lib/api";
import { formatSeconds } from "@/lib/utils";
import { GestureOverlay } from "@/components/gesture/GestureOverlay";
import { AnnotationLayer } from "@/components/consultation/AnnotationLayer";
import { ReportViewer } from "@/components/consultation/ReportViewer";
import { VisionPanel } from "@/components/consultation/VisionPanel";
import { Modal } from "@/components/ui/Modal";
import type { Annotation, GestureResult, AppNotification } from "@/types";

interface Props {
  consultationId: string;
  roomId: string;
}

export default function ConsultationRoom({ consultationId, roomId }: Props) {
  const { user } = useAuthStore();
  const isDoctor = user?.role === "DOCTOR";

  // Video refs
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);

  // UI state
  const [videoEnabled, setVideoEnabled] = useState(true);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [currentGesture, setCurrentGesture] = useState<GestureResult | null>(null);
  const [participantCount, setParticipantCount] = useState(1);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [ended, setEnded] = useState(false);
  const [reportGenerating, setReportGenerating] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [drawMode, setDrawMode] = useState(false);
  const [containerSize, setContainerSize] = useState({ width: 1280, height: 720 });
  const videoContainerRef = useRef<HTMLDivElement>(null);

  // Measure container for annotation layer
  useEffect(() => {
    const obs = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setContainerSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    if (videoContainerRef.current) obs.observe(videoContainerRef.current);
    return () => obs.disconnect();
  }, []);

  // ── Timer ──────────────────────────────────────────────────────
  useEffect(() => {
    const t = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // ── Notification helpers ───────────────────────────────────────
  const addNotification = useCallback(
    (message: string, level: AppNotification["level"] = "info") => {
      const id = `n_${Date.now()}`;
      setNotifications((prev) => [{ id, message, level }, ...prev].slice(0, 3));
      setTimeout(() => setNotifications((prev) => prev.filter((n) => n.id !== id)), 4500);
    },
    []
  );

  // ── Socket ─────────────────────────────────────────────────────
  const socketActions = useConsultationSocket({
    roomId,
    onUserJoined: ({ role }) => {
      setParticipantCount((p) => p + 1);
      addNotification(`${role === "DOCTOR" ? "Doctor" : "Patient"} joined`, "success");
      if (role === "DOCTOR" && !isDoctor) webrtc.startCall();
    },
    onUserLeft: ({ role }) => {
      setParticipantCount((p) => Math.max(1, p - 1));
      addNotification(`${role === "DOCTOR" ? "Doctor" : "Patient"} left`, "warning");
    },
    onGesture: (event: GestureEvent) => {
      setCurrentGesture({
        gesture: event.gesture as GestureResult["gesture"],
        confidence: event.confidence,
        hands_detected: 1,
        metadata: event.metadata,
      });
      setTimeout(() => setCurrentGesture(null), 2500);
    },
    onAnnotation: (event: AnnotationEvent) => {
      const ann: Annotation = {
        id: event.id,
        type: event.type as Annotation["type"],
        coordinates: event.coordinates as Annotation["coordinates"],
        body_region: event.body_region,
        note: event.note,
        color: event.color,
        created_by: event.created_by,
        role: event.role as Annotation["role"],
        timestamp: event.timestamp,
      };
      setAnnotations((prev) => [...prev, ann]);
    },
    onAnnotationRemoved: ({ annotation_id }) => {
      setAnnotations((prev) => prev.filter((a) => a.id !== annotation_id));
    },
    onAnnotationsCleared: () => setAnnotations([]),
    onPatientAction: ({ action, pain_level, message }) => {
      if (action?.startsWith("PAIN_")) {
        addNotification(
          `Patient pain level: ${pain_level}/5`,
          (pain_level ?? 0) >= 4 ? "critical" : "warning"
        );
      } else {
        const levelMap: Record<string, AppNotification["level"]> = {
          NURSE_CALLED: "success",
          EMERGENCY: "critical",
          WATER_REQUESTED: "info",
          ASSISTANCE_NEEDED: "warning",
        };
        addNotification(message || action, levelMap[action] ?? "info");
      }
    },
    onConsultationEnded: async () => {
      setEnded(true);
      setReportGenerating(true);
      addNotification("Consultation ended — generating AI report…", "info");
      try {
        await reportApi.generate(consultationId);
        addNotification("AI report ready!", "success");
      } catch {
        addNotification("Report generation failed", "warning");
      } finally {
        setReportGenerating(false);
      }
    },
    onWebRTCOffer: ({ offer }) => webrtc.handleOffer(offer),
    onWebRTCAnswer: ({ answer }) => webrtc.handleAnswer(answer),
    onICECandidate: ({ candidate }) => webrtc.handleICECandidate(candidate),
  });

  // ── WebRTC ─────────────────────────────────────────────────────
  const webrtc = useWebRTC({
    isInitiator: isDoctor,
    onOffer: (offer) => socketActions.sendOffer(offer),
    onAnswer: (answer) => socketActions.sendAnswer(answer),
    onICECandidate: (c) => socketActions.sendICECandidate(c),
  });

  // Attach streams
  useEffect(() => {
    if (localVideoRef.current && webrtc.localStream) {
      localVideoRef.current.srcObject = webrtc.localStream;
    }
  }, [webrtc.localStream]);

  useEffect(() => {
    if (remoteVideoRef.current && webrtc.remoteStream) {
      remoteVideoRef.current.srcObject = webrtc.remoteStream;
    }
  }, [webrtc.remoteStream]);

  // ── Gesture Camera ─────────────────────────────────────────────
  const gestureCamera = useGestureCamera({
    enabled: !ended,
    consultationId,
    userId: user?.id ?? "",
    userRole: user?.role ?? "PATIENT",
    emitFrame: socketActions.emitFrame,
    onGestureResult: (result) => {
      setCurrentGesture(result);
      if (result.action) {
        addNotification(result.action.message, result.action.level);
      }
    },
    fps: 10,
  });

  // Init: start local stream, join call
  useEffect(() => {
    webrtc.initLocalStream().then(() => {
      if (isDoctor) webrtc.startCall();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Annotation handlers ────────────────────────────────────────
  const handleAddAnnotation = useCallback(
    (ann: Omit<Annotation, "created_by" | "role" | "timestamp">) => {
      socketActions.emitAnnotation({
        id: ann.id,
        type: ann.type,
        coordinates: ann.coordinates as unknown as Record<string, number>,
        body_region: ann.body_region,
        note: ann.note,
        color: ann.color ?? "#FF6B6B",
      });
    },
    [socketActions]
  );

  const handleRemoveAnnotation = useCallback(
    (id: string) => socketActions.removeAnnotation(id),
    [socketActions]
  );

  const handleClearAnnotations = useCallback(
    () => socketActions.clearAnnotations(),
    [socketActions]
  );

  const handleEndConsultation = async () => {
    socketActions.endConsultation(consultationId);
    await consultationApi.update(consultationId, { status: "COMPLETED" });
  };

  return (
    <div className="relative w-full h-screen bg-[#060608] overflow-hidden font-mono select-none">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-950/15 via-transparent to-purple-950/15 pointer-events-none" />

      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between px-6 py-3.5 bg-black/50 backdrop-blur-md border-b border-white/5">
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] text-white/50 uppercase tracking-widest">Live</span>
          </div>
          <div className="flex items-center gap-2 text-white/35">
            <Clock className="w-3.5 h-3.5" />
            <span className="text-sm tabular-nums">{formatSeconds(elapsedSeconds)}</span>
          </div>
          <div className="flex items-center gap-2 text-white/35">
            <Users className="w-3.5 h-3.5" />
            <span className="text-sm">{participantCount}</span>
          </div>
        </div>

        <span className="text-white/60 text-xs tracking-widest uppercase">GestureMed AI</span>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] text-white/40 uppercase tracking-wider">
            {isDoctor ? "Doctor" : "Patient"}
          </span>
          {gestureCamera.isCapturing && (
            <span className="px-2.5 py-1 rounded-full bg-purple-500/15 border border-purple-500/25 text-[10px] text-purple-400 flex items-center gap-1.5">
              <Hand className="w-3 h-3" />
              Gesture Active
            </span>
          )}
        </div>
      </div>

      {/* ── Video + Annotation Area ──────────────────────────────── */}
      <div ref={videoContainerRef} className="absolute inset-0 pt-14 pb-20">
        {/* Remote video (main) */}
        <video
          ref={remoteVideoRef}
          autoPlay
          playsInline
          className="w-full h-full object-cover"
        />

        {/* No remote stream placeholder */}
        {!webrtc.remoteStream && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#08080f]">
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-white/4 border border-white/8 flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-white/20" />
              </div>
              <p className="text-white/25 text-sm">Waiting for participant…</p>
            </div>
          </div>
        )}

        {/* Annotation Layer (doctor only, SVG overlay) */}
        {isDoctor && (
          <AnnotationLayer
            annotations={annotations}
            drawMode={drawMode}
            isDoctor={isDoctor}
            containerWidth={containerSize.width}
            containerHeight={containerSize.height}
            onAddAnnotation={handleAddAnnotation}
            onRemoveAnnotation={handleRemoveAnnotation}
            onClearAnnotations={handleClearAnnotations}
            className="absolute inset-0"
          />
        )}

        {/* Gesture Overlay (HUD + notifications) */}
        <GestureOverlay
          currentGesture={currentGesture}
          notifications={notifications}
          role={user?.role ?? "PATIENT"}
        />

        {/* Local video PiP */}
        <div className="absolute bottom-4 right-4 w-44 h-32 rounded-2xl overflow-hidden border border-white/10 bg-black shadow-2xl z-20">
          <video ref={localVideoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
          {!videoEnabled && (
            <div className="absolute inset-0 bg-[#08080f] flex items-center justify-center">
              <VideoOff className="w-6 h-6 text-white/25" />
            </div>
          )}
          {/* Hidden gesture camera video (offscreen) */}
          <video ref={gestureCamera.videoRef} autoPlay playsInline muted className="hidden" />
        </div>

        {/* Vision pipeline panel (doctor only) */}
        {isDoctor && (
          <div className="absolute left-4 bottom-4 w-72 z-20">
            <VisionPanel consultationId={consultationId} />
          </div>
        )}

        {/* Annotation list (doctor sidebar) */}
        {isDoctor && annotations.length > 0 && (
          <div className="absolute left-4 top-4 w-52 bg-black/65 backdrop-blur-md rounded-xl border border-white/8 p-3 z-20">
            <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2 flex items-center gap-1.5">
              <Pencil className="w-3 h-3" />
              Annotations ({annotations.length})
            </p>
            <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto">
              {annotations.map((a) => (
                <div key={a.id} className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: a.color }} />
                    <span className="text-xs text-white/50 truncate">{a.body_region ?? a.note ?? "Mark"}</span>
                  </div>
                  <button
                    onClick={() => handleRemoveAnnotation(a.id)}
                    className="text-white/20 hover:text-red-400 transition-colors flex-shrink-0"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Controls Bar ────────────────────────────────────────── */}
      <div className="absolute bottom-0 left-0 right-0 z-30 flex items-center justify-center gap-3 px-6 py-4 bg-black/65 backdrop-blur-md border-t border-white/5">
        {/* Audio */}
        <button
          onClick={() => {
            setAudioEnabled((v) => !v);
            webrtc.toggleAudio(!audioEnabled);
          }}
          className={`p-3 rounded-xl border transition-all ${
            audioEnabled
              ? "bg-white/5 border-white/10 text-white/55 hover:bg-white/8"
              : "bg-red-500/15 border-red-500/30 text-red-400"
          }`}
        >
          {audioEnabled ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
        </button>

        {/* Video */}
        <button
          onClick={() => {
            setVideoEnabled((v) => !v);
            webrtc.toggleVideo(!videoEnabled);
          }}
          className={`p-3 rounded-xl border transition-all ${
            videoEnabled
              ? "bg-white/5 border-white/10 text-white/55 hover:bg-white/8"
              : "bg-red-500/15 border-red-500/30 text-red-400"
          }`}
        >
          {videoEnabled ? <Video className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
        </button>

        {/* Doctor-only tools */}
        {isDoctor && (
          <>
            <div className="w-px h-8 bg-white/8" />
            <button
              onClick={() => setDrawMode((v) => !v)}
              className={`p-3 rounded-xl border transition-all ${
                drawMode
                  ? "bg-blue-500/15 border-blue-500/35 text-blue-400"
                  : "bg-white/5 border-white/10 text-white/55 hover:bg-white/8"
              }`}
              title="Toggle draw mode"
            >
              <Pencil className="w-5 h-5" />
            </button>

            <button
              onClick={handleClearAnnotations}
              className="p-3 rounded-xl border bg-white/5 border-white/10 text-white/55 hover:bg-white/8 transition-all"
              title="Clear all annotations"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </>
        )}

        <div className="w-px h-8 bg-white/8" />

        {/* End call */}
        {isDoctor ? (
          <button
            onClick={handleEndConsultation}
            disabled={ended}
            className="flex items-center gap-2 px-5 py-3 rounded-xl bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PhoneOff className="w-4 h-4" />
            End Consultation
          </button>
        ) : (
          <button
            onClick={webrtc.endCall}
            className="flex items-center gap-2 px-5 py-3 rounded-xl bg-red-500/15 border border-red-500/30 text-red-400 hover:bg-red-500/25 text-sm transition-all"
          >
            <PhoneOff className="w-4 h-4" />
            Leave
          </button>
        )}

        {/* View report button */}
        {ended && (
          <button
            onClick={() => setShowReport(true)}
            className="flex items-center gap-2 px-4 py-3 rounded-xl bg-purple-500/15 border border-purple-500/25 text-purple-400 hover:bg-purple-500/25 text-sm transition-all"
          >
            <FileText className="w-4 h-4" />
            {reportGenerating ? "Generating…" : "View Report"}
          </button>
        )}
      </div>

      {/* ── Ended overlay ────────────────────────────────────────── */}
      <AnimatePresence>
        {ended && !showReport && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-40 bg-black/75 backdrop-blur-md flex items-center justify-center pointer-events-none"
          >
            <div className="text-center pointer-events-auto">
              <div className="w-16 h-16 rounded-full bg-emerald-500/15 border border-emerald-500/25 flex items-center justify-center mx-auto mb-5">
                <Activity className="w-7 h-7 text-emerald-400" />
              </div>
              <h2 className="text-xl text-white font-light mb-1.5">Consultation Complete</h2>
              <p className="text-white/35 text-sm mb-6">
                {reportGenerating ? "AI is generating your report…" : "Report ready — check your dashboard"}
              </p>
              {reportGenerating && (
                <div className="w-40 h-0.5 bg-white/8 rounded-full mx-auto overflow-hidden">
                  <motion.div
                    className="h-full bg-purple-400 rounded-full"
                    animate={{ x: ["-100%", "200%"] }}
                    transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
                  />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Report Modal */}
      <Modal
        open={showReport}
        onClose={() => setShowReport(false)}
        title="AI Consultation Report"
        size="lg"
      >
        <ReportViewer consultationId={consultationId} />
      </Modal>
    </div>
  );
}
