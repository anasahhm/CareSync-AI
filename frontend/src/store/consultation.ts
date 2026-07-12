/**
 * GestureMed AI — Consultation Store (Zustand)
 * Manages active consultation session state.
 */
import { create } from "zustand";
import type { Annotation, AppNotification, GestureResult, ConsultationStatus } from "@/types";

interface ConsultationState {
  // Session
  consultationId: string | null;
  roomId: string | null;
  status: ConsultationStatus | null;
  elapsedSeconds: number;
  participantCount: number;

  // Media
  videoEnabled: boolean;
  audioEnabled: boolean;
  isConnected: boolean;

  // Annotations
  annotations: Annotation[];

  // Gestures
  lastGesture: GestureResult | null;

  // Notifications
  notifications: AppNotification[];

  // Doctor tools
  drawMode: boolean;
  zoomLevel: number;

  // Actions
  setSession: (consultationId: string, roomId: string) => void;
  setStatus: (status: ConsultationStatus) => void;
  setConnected: (connected: boolean) => void;
  toggleVideo: () => void;
  toggleAudio: () => void;
  setParticipantCount: (count: number) => void;
  tickTimer: () => void;
  resetTimer: () => void;

  addAnnotation: (annotation: Annotation) => void;
  removeAnnotation: (id: string) => void;
  clearAnnotations: () => void;
  setAnnotations: (annotations: Annotation[]) => void;

  setLastGesture: (gesture: GestureResult) => void;

  addNotification: (message: string, level: AppNotification["level"]) => void;
  removeNotification: (id: string) => void;

  setDrawMode: (enabled: boolean) => void;
  setZoomLevel: (level: number) => void;

  reset: () => void;
}

const initialState = {
  consultationId: null,
  roomId: null,
  status: null,
  elapsedSeconds: 0,
  participantCount: 1,
  videoEnabled: true,
  audioEnabled: true,
  isConnected: false,
  annotations: [],
  lastGesture: null,
  notifications: [],
  drawMode: false,
  zoomLevel: 1.0,
};

export const useConsultationStore = create<ConsultationState>((set, get) => ({
  ...initialState,

  setSession: (consultationId, roomId) => set({ consultationId, roomId }),
  setStatus: (status) => set({ status }),
  setConnected: (isConnected) => set({ isConnected }),

  toggleVideo: () => set((s) => ({ videoEnabled: !s.videoEnabled })),
  toggleAudio: () => set((s) => ({ audioEnabled: !s.audioEnabled })),
  setParticipantCount: (participantCount) => set({ participantCount }),

  tickTimer: () => set((s) => ({ elapsedSeconds: s.elapsedSeconds + 1 })),
  resetTimer: () => set({ elapsedSeconds: 0 }),

  addAnnotation: (annotation) =>
    set((s) => ({ annotations: [...s.annotations, annotation] })),
  removeAnnotation: (id) =>
    set((s) => ({ annotations: s.annotations.filter((a) => a.id !== id) })),
  clearAnnotations: () => set({ annotations: [] }),
  setAnnotations: (annotations) => set({ annotations }),

  setLastGesture: (lastGesture) => set({ lastGesture }),

  addNotification: (message, level) => {
    const id = `notif_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const notification: AppNotification = { id, message, level, timestamp: new Date().toISOString() };
    set((s) => ({ notifications: [notification, ...s.notifications].slice(0, 5) }));
    setTimeout(() => get().removeNotification(id), 4500);
    return id;
  },
  removeNotification: (id) =>
    set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) })),

  setDrawMode: (drawMode) => set({ drawMode }),
  setZoomLevel: (zoomLevel) => set({ zoomLevel }),

  reset: () => set(initialState),
}));
