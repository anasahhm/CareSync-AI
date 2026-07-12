import { HTMLAttributes } from "react";
import { cn, getInitials } from "@/lib/utils";

type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";

interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  name?: string;
  src?: string;
  size?: AvatarSize;
  role?: "PATIENT" | "DOCTOR" | "ADMIN";
  online?: boolean;
}

const sizeClasses: Record<AvatarSize, string> = {
  xs: "w-6 h-6 text-[10px]",
  sm: "w-8 h-8 text-xs",
  md: "w-10 h-10 text-sm",
  lg: "w-12 h-12 text-base",
  xl: "w-16 h-16 text-xl",
};

const roleGradients: Record<string, string> = {
  PATIENT: "from-blue-600 to-blue-800",
  DOCTOR:  "from-teal-600 to-teal-800",
  ADMIN:   "from-purple-600 to-purple-800",
};

const dotSizes: Record<AvatarSize, string> = {
  xs: "w-1.5 h-1.5",
  sm: "w-2 h-2",
  md: "w-2.5 h-2.5",
  lg: "w-3 h-3",
  xl: "w-3.5 h-3.5",
};

export function Avatar({ name, src, size = "md", role = "PATIENT", online, className, ...props }: AvatarProps) {
  const gradient = roleGradients[role] ?? roleGradients.PATIENT;
  const initials = name ? getInitials(name) : "?";

  return (
    <div className={cn("relative flex-shrink-0", className)} {...props}>
      <div
        className={cn(
          "rounded-full flex items-center justify-center font-semibold text-white",
          `bg-gradient-to-br ${gradient}`,
          sizeClasses[size]
        )}
      >
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element -- avatar `src` is an arbitrary external URL; next/image would require remotePatterns for every possible avatar host in advance
          <img src={src} alt={name} className="w-full h-full rounded-full object-cover" />
        ) : (
          <span className="font-mono">{initials}</span>
        )}
      </div>
      {online !== undefined && (
        <span
          className={cn(
            "absolute bottom-0 right-0 rounded-full border-2 border-[#060608]",
            dotSizes[size],
            online ? "bg-emerald-400" : "bg-slate-600"
          )}
        />
      )}
    </div>
  );
}
