import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "purple" | "outline";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  dot?: boolean;
  size?: "sm" | "md";
}

const variantClasses: Record<BadgeVariant, string> = {
  default:  "bg-white/8 text-white/60 border-white/10",
  success:  "bg-emerald-500/12 text-emerald-400 border-emerald-500/20",
  warning:  "bg-amber-500/12 text-amber-400 border-amber-500/20",
  danger:   "bg-red-500/12 text-red-400 border-red-500/20",
  info:     "bg-blue-500/12 text-blue-400 border-blue-500/20",
  purple:   "bg-purple-500/12 text-purple-400 border-purple-500/20",
  outline:  "bg-transparent text-white/50 border-[#252535]",
};

const dotColors: Record<BadgeVariant, string> = {
  default:  "bg-white/40",
  success:  "bg-emerald-400",
  warning:  "bg-amber-400",
  danger:   "bg-red-400",
  info:     "bg-blue-400",
  purple:   "bg-purple-400",
  outline:  "bg-white/40",
};

const sizeClasses = {
  sm: "px-2 py-0.5 text-[10px] gap-1",
  md: "px-2.5 py-1 text-xs gap-1.5",
};

export function Badge({ variant = "default", dot = false, size = "md", className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center font-medium border rounded-full",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {dot && (
        <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", dotColors[variant])} />
      )}
      {children}
    </span>
  );
}
