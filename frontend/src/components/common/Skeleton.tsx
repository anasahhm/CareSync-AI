import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-white/8", className)} />;
}

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={cn("h-3", i === lines - 1 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  );
}

/** Generic card-shaped skeleton for panels that show a title + a few rows of stats */
export function CardSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-4 space-y-3">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center justify-between">
          <Skeleton className="h-3 w-1/4" />
          <Skeleton className="h-3 w-1/5" />
        </div>
      ))}
    </div>
  );
}

export function GPULoadingSkeleton() {
  return <CardSkeleton rows={4} />;
}

export function VisionLoadingSkeleton() {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-7 w-16 rounded-lg" />
      </div>
      <Skeleton className="h-32 w-full rounded-lg" />
      <SkeletonText lines={2} />
    </div>
  );
}

export function AgentTimelineSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-xl border border-white/8 bg-white/[0.02] p-3">
          <Skeleton className="h-8 w-8 rounded-full flex-shrink-0" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-2.5 w-1/2" />
          </div>
          <Skeleton className="h-5 w-14 rounded-full flex-shrink-0" />
        </div>
      ))}
    </div>
  );
}

export function ReportLoadingSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-white/8 bg-white/[0.02] p-4 space-y-2">
          <Skeleton className="h-3 w-1/4" />
          <SkeletonText lines={2} />
        </div>
      ))}
    </div>
  );
}

export function RAGLoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="rounded-xl border border-white/8 bg-white/[0.02] p-3 space-y-2">
          <div className="flex items-center justify-between">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-3 w-10" />
          </div>
          <SkeletonText lines={2} />
        </div>
      ))}
    </div>
  );
}

export function MemoryLoadingSkeleton() {
  return (
    <div className="space-y-3">
      <CardSkeleton rows={3} />
      <div className="flex flex-wrap gap-1.5">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-6 w-20 rounded-full" />
        ))}
      </div>
    </div>
  );
}
