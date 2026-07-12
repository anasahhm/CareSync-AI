/**
 * GestureMed AI — Socket.IO Client Hook
 * Manages real-time consultation room connection.
 */
"use client";

import { useEffect, useRef, useCallback } from "react";
import { io, Socket } from "socket.io-client";
import { useAuthStore } from "@/store/auth";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "http://localhost:8000";

export interface GestureEvent {
  gesture: string;
  confidence: number;
  action?: string;
  metadata: Record<string, unknown>;
  user_id: string;
  role: string;
  timestamp: string;
}

export interface AnnotationEvent {
  id: string;
  type: string;
  coordinates: Record<string, number>;
  body_region?: string;
  note?: string;
  color: string;
  created_by: string;
  role: string;
  timestamp: string;
}

interface UseConsultationSocketOptions {
  roomId: string | null;
  onUserJoined?: (data: { user_id: string; role: string }) => void;
  onUserLeft?: (data: { user_id: string; role: string }) => void;
  onGesture?: (event: GestureEvent) => void;
  onAnnotation?: (event: AnnotationEvent) => void;
  onAnnotationRemoved?: (data: { annotation_id: string }) => void;
  onAnnotationsCleared?: () => void;
  onPatientAction?: (data: { action: string; pain_level?: number; message?: string }) => void;
  onConsultationEnded?: (data: { ended_by: string; consultation_id: string }) => void;
  // WebRTC
  onWebRTCOffer?: (data: { offer: RTCSessionDescriptionInit; from_sid: string }) => void;
  onWebRTCAnswer?: (data: { answer: RTCSessionDescriptionInit; from_sid: string }) => void;
  onICECandidate?: (data: { candidate: RTCIceCandidateInit; from_sid: string }) => void;
}

export function useConsultationSocket(options: UseConsultationSocketOptions) {
  const socketRef = useRef<Socket | null>(null);
  const { accessToken } = useAuthStore();

  useEffect(() => {
    if (!accessToken || !options.roomId) return;

    const socket = io(WS_URL, {
      auth: { token: accessToken },
      transports: ["websocket"],
    });

    socketRef.current = socket;

    socket.on("connect", () => {
      socket.emit("join_room", { room_id: options.roomId }, (response: unknown) => {
        console.log("[Socket] Joined room:", response);
      });
    });

    socket.on("user_joined", options.onUserJoined ?? (() => {}));
    socket.on("user_left", options.onUserLeft ?? (() => {}));
    socket.on("gesture_received", options.onGesture ?? (() => {}));
    socket.on("annotation_added", options.onAnnotation ?? (() => {}));
    socket.on("annotation_removed", options.onAnnotationRemoved ?? (() => {}));
    socket.on("annotations_cleared", options.onAnnotationsCleared ?? (() => {}));
    socket.on("patient_action_received", options.onPatientAction ?? (() => {}));
    socket.on("consultation_ended", options.onConsultationEnded ?? (() => {}));
    socket.on("webrtc_offer", options.onWebRTCOffer ?? (() => {}));
    socket.on("webrtc_answer", options.onWebRTCAnswer ?? (() => {}));
    socket.on("ice_candidate", options.onICECandidate ?? (() => {}));

    socket.on("disconnect", () => {
      console.log("[Socket] Disconnected");
    });

    return () => {
      socket.emit("leave_room", { room_id: options.roomId });
      socket.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, options.roomId]);

  // ── Emit helpers ────────────────────────────────────────────────────────────

  const emitGesture = useCallback((gesture: string, confidence: number, action?: string, metadata?: object) => {
    socketRef.current?.emit("gesture_event", { gesture, confidence, action, metadata: metadata ?? {} });
  }, []);

  const emitFrame = useCallback((frameB64: string, consultationId: string) => {
    socketRef.current?.emit("gesture_frame", {
      frame: frameB64,
      consultation_id: consultationId,
    });
  }, []);

  const emitAnnotation = useCallback((annotation: Omit<AnnotationEvent, "created_by" | "role" | "timestamp">) => {
    socketRef.current?.emit("add_annotation", annotation);
  }, []);

  const clearAnnotations = useCallback(() => {
    socketRef.current?.emit("clear_annotations", {});
  }, []);

  const removeAnnotation = useCallback((annotationId: string) => {
    socketRef.current?.emit("remove_annotation", { annotation_id: annotationId });
  }, []);

  const emitPatientAction = useCallback((action: string, pain_level?: number, message?: string) => {
    socketRef.current?.emit("patient_action", { action, pain_level, message });
  }, []);

  const endConsultation = useCallback((consultationId: string) => {
    socketRef.current?.emit("end_consultation", { consultation_id: consultationId });
  }, []);

  // WebRTC
  const sendOffer = useCallback((offer: RTCSessionDescriptionInit) => {
    socketRef.current?.emit("webrtc_offer", { offer });
  }, []);

  const sendAnswer = useCallback((answer: RTCSessionDescriptionInit) => {
    socketRef.current?.emit("webrtc_answer", { answer });
  }, []);

  const sendICECandidate = useCallback((candidate: RTCIceCandidateInit) => {
    socketRef.current?.emit("ice_candidate", { candidate });
  }, []);

  return {
    socket: socketRef.current,
    emitGesture,
    emitFrame,
    emitAnnotation,
    clearAnnotations,
    removeAnnotation,
    emitPatientAction,
    endConsultation,
    sendOffer,
    sendAnswer,
    sendICECandidate,
  };
}
