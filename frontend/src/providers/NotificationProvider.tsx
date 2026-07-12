"use client";

import { createContext, useCallback, useContext, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, AlertTriangle, XCircle, Info, X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type NotificationType = "success" | "warning" | "error" | "info" | "loading";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  /** ms before auto-dismiss; 0 = sticky (must be dismissed manually or updated) */
  duration?: number;
}

interface NotificationContextValue {
  notify: (notification: Omit<Notification, "id"> & { id?: string }) => string;
  update: (id: string, patch: Partial<Omit<Notification, "id">>) => void;
  dismiss: (id: string) => void;
  clear: () => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

const DEFAULT_DURATIONS: Record<NotificationType, number> = {
  success: 4000,
  info: 4000,
  warning: 6000,
  error: 7000,
  loading: 0,
};

const ICONS: Record<NotificationType, typeof CheckCircle2> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
  info: Info,
  loading: Loader2,
};

const COLORS: Record<NotificationType, string> = {
  success: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300",
  warning: "border-amber-500/25 bg-amber-500/10 text-amber-300",
  error: "border-red-500/25 bg-red-500/10 text-red-300",
  info: "border-blue-500/25 bg-blue-500/10 text-blue-300",
  loading: "border-white/15 bg-white/5 text-white/70",
};

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const scheduleDismiss = useCallback((id: string, duration: number) => {
    const existing = timers.current.get(id);
    if (existing) clearTimeout(existing);
    if (duration > 0) {
      const timer = setTimeout(() => dismiss(id), duration);
      timers.current.set(id, timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const notify = useCallback<NotificationContextValue["notify"]>((notification) => {
    const id = notification.id ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const duration = notification.duration ?? DEFAULT_DURATIONS[notification.type];

    setNotifications((prev) => {
      const withoutExisting = prev.filter((n) => n.id !== id);
      return [...withoutExisting, { ...notification, id, duration }].slice(-5);
    });

    scheduleDismiss(id, duration);
    return id;
  }, [scheduleDismiss]);

  const update = useCallback<NotificationContextValue["update"]>((id, patch) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, ...patch } : n))
    );
    if (patch.type || patch.duration !== undefined) {
      const resolvedType = patch.type ?? "info";
      const duration = patch.duration ?? DEFAULT_DURATIONS[resolvedType];
      scheduleDismiss(id, duration);
    }
  }, [scheduleDismiss]);

  const dismiss = useCallback((id: string) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clear = useCallback(() => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current.clear();
    setNotifications([]);
  }, []);

  return (
    <NotificationContext.Provider value={{ notify, update, dismiss, clear }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80 max-w-[calc(100vw-2rem)]">
        <AnimatePresence>
          {notifications.map((n) => {
            const Icon = ICONS[n.type];
            return (
              <motion.div
                key={n.id}
                initial={{ opacity: 0, x: 24, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 24, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                className={cn(
                  "flex items-start gap-2.5 p-3 rounded-xl border backdrop-blur-md shadow-lg",
                  COLORS[n.type]
                )}
              >
                <Icon className={cn("w-4 h-4 flex-shrink-0 mt-0.5", n.type === "loading" && "animate-spin")} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium leading-tight">{n.title}</p>
                  {n.message && <p className="text-xs opacity-70 mt-0.5 leading-snug">{n.message}</p>}
                </div>
                <button
                  onClick={() => dismiss(n.id)}
                  className="opacity-50 hover:opacity-90 transition-opacity flex-shrink-0"
                  aria-label="Dismiss notification"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotifications must be used within a NotificationProvider");
  return ctx;
}
