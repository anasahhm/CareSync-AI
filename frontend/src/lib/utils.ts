import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind class names safely. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format seconds into mm:ss or h:mm:ss */
export function formatSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

/** Format ISO date string into readable format */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Format ISO date string with time */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Get initials from full name */
export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

/** Notification level → Tailwind color classes */
export function notificationColors(level: string) {
  const map: Record<string, { border: string; bg: string; text: string; dot: string }> = {
    info: {
      border: "border-blue-500/30",
      bg: "bg-blue-500/10",
      text: "text-blue-300",
      dot: "bg-blue-400",
    },
    success: {
      border: "border-emerald-500/30",
      bg: "bg-emerald-500/10",
      text: "text-emerald-300",
      dot: "bg-emerald-400",
    },
    warning: {
      border: "border-amber-500/30",
      bg: "bg-amber-500/10",
      text: "text-amber-300",
      dot: "bg-amber-400",
    },
    critical: {
      border: "border-red-500/50",
      bg: "bg-red-500/15",
      text: "text-red-300",
      dot: "bg-red-400",
    },
  };
  return map[level] ?? map.info;
}

/** Status → display string */
export function consultationStatusLabel(status: string): string {
  const map: Record<string, string> = {
    SCHEDULED: "Scheduled",
    WAITING: "Waiting",
    ACTIVE: "In Progress",
    COMPLETED: "Completed",
    CANCELLED: "Cancelled",
  };
  return map[status] ?? status;
}

/** Status → color classes */
export function consultationStatusColor(status: string): string {
  const map: Record<string, string> = {
    SCHEDULED: "text-blue-400 bg-blue-400/10 border-blue-400/20",
    WAITING: "text-amber-400 bg-amber-400/10 border-amber-400/20",
    ACTIVE: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
    COMPLETED: "text-slate-400 bg-slate-400/10 border-slate-400/20",
    CANCELLED: "text-red-400 bg-red-400/10 border-red-400/20",
  };
  return map[status] ?? "text-slate-400 bg-slate-400/10 border-slate-400/20";
}
