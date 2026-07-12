"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Hand, Zap } from "lucide-react";
import { cn, notificationColors } from "@/lib/utils";
import type { GestureResult, UserRole, AppNotification } from "@/types";

interface GestureOverlayProps {
  currentGesture: GestureResult | null;
  notifications: AppNotification[];
  role: UserRole;
  className?: string;
}

const GESTURE_LABELS: Record<string, string> = {
  PINCH:       "Pinch",
  PEACE:       "Peace ✌️",
  POINTING:    "Pointing ☝️",
  THUMBS_UP:   "Thumbs Up 👍",
  THUMBS_DOWN: "Thumbs Down 👎",
  OPEN_PALM:   "Open Palm 🖐️",
  FIST:        "Fist ✊",
  FINGERS_1:   "1 Finger",
  FINGERS_2:   "2 Fingers",
  FINGERS_3:   "3 Fingers",
  FINGERS_4:   "4 Fingers",
  FINGERS_5:   "5 Fingers",
  NONE:        "No gesture",
};

const PATIENT_GUIDE = [
  { gesture: "PEACE",       action: "Call nurse (hold 1s)" },
  { gesture: "FINGERS_1–5", action: "Report pain level" },
  { gesture: "PINCH",       action: "Request water" },
  { gesture: "THUMBS_UP",   action: "Feeling good" },
  { gesture: "THUMBS_DOWN", action: "Need help" },
  { gesture: "OPEN_PALM",   action: "Emergency (hold 2.5s)" },
];

const DOCTOR_GUIDE = [
  { gesture: "POINTING",    action: "Mark body area" },
  { gesture: "PINCH",       action: "Zoom in (hold)" },
  { gesture: "OPEN_PALM",   action: "Zoom out" },
  { gesture: "THUMBS_UP",   action: "Approve" },
  { gesture: "THUMBS_DOWN", action: "Reject" },
  { gesture: "PEACE",       action: "Next patient record" },
  { gesture: "FIST",        action: "Clear annotations" },
];

export function GestureOverlay({ currentGesture, notifications, role, className }: GestureOverlayProps) {
  const guide = role === "DOCTOR" ? DOCTOR_GUIDE : PATIENT_GUIDE;
  const accentColor = role === "DOCTOR" ? "text-teal-400 border-teal-500/30 bg-teal-500/10" : "text-blue-400 border-blue-500/30 bg-blue-500/10";

  return (
    <div className={cn("absolute inset-0 pointer-events-none z-10", className)}>
      {/* ── Notifications (top center) ───────────────────────── */}
      <div className="absolute top-20 left-1/2 -translate-x-1/2 flex flex-col gap-2 w-80 max-w-[90vw]">
        <AnimatePresence>
          {notifications.slice(0, 3).map((n) => {
            const colors = notificationColors(n.level);
            return (
              <motion.div
                key={n.id}
                initial={{ opacity: 0, y: -12, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.95 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md text-sm font-medium",
                  colors.border, colors.bg, colors.text
                )}
              >
                <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse", colors.dot)} />
                {n.message}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* ── Current gesture badge (top right) ────────────────── */}
      <AnimatePresence>
        {currentGesture && currentGesture.gesture !== "NONE" && (
          <motion.div
            key={currentGesture.gesture}
            initial={{ opacity: 0, scale: 0.85, x: 10 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.85, x: 10 }}
            transition={{ duration: 0.2 }}
            className={cn(
              "absolute top-20 right-4 flex items-center gap-2.5 px-3 py-2 rounded-xl border backdrop-blur-md",
              accentColor
            )}
          >
            <Hand className="w-3.5 h-3.5 flex-shrink-0" />
            <div className="flex flex-col">
              <span className="text-xs font-semibold leading-tight">
                {GESTURE_LABELS[currentGesture.gesture] ?? currentGesture.gesture}
              </span>
              <span className="text-[10px] opacity-60">
                {Math.round(currentGesture.confidence * 100)}% confidence
              </span>
            </div>
            {currentGesture.action && (
              <div className="flex items-center gap-1 ml-1 pl-2 border-l border-current/20">
                <Zap className="w-3 h-3" />
                <span className="text-[10px] font-medium">{currentGesture.action.type}</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Gesture guide panel (bottom left) ────────────────── */}
      <div className="absolute bottom-24 left-4 bg-black/60 backdrop-blur-md rounded-xl border border-white/8 p-4 w-56">
        <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-3">
          {role === "DOCTOR" ? "Doctor" : "Patient"} Gestures
        </p>
        <div className="flex flex-col gap-2">
          {guide.map(({ gesture, action }) => (
            <div key={gesture} className="flex items-start justify-between gap-2">
              <span className="text-[10px] font-mono text-white/50 flex-shrink-0 w-20 leading-tight">{gesture}</span>
              <span className="text-[10px] text-white/30 text-right leading-tight">{action}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
