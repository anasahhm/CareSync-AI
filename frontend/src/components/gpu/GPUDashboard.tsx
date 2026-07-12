"use client";

import { useQuery } from "@tanstack/react-query";
import { Cpu, Zap, Activity, AlertTriangle } from "lucide-react";
import { gpuApi } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

interface GPUStatusResponse {
  device: {
    torch_available: boolean;
    backend: "cpu" | "cuda" | "rocm";
    device_str: string;
    device_name: string;
    is_rocm: boolean;
    is_cuda: boolean;
    device_count: number;
  };
  metrics: Record<string, unknown> & { source: string; note?: string };
  health: { healthy: boolean; backend: string; reason: string };
}

export function GPUDashboard() {
  const { data, isLoading, isError } = useQuery<GPUStatusResponse>({
    queryKey: ["gpu-status"],
    queryFn: async () => {
      const { data } = await gpuApi.status();
      return data;
    },
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <Card padding="md">
        <CardContent>
          <p className="text-white/40 text-sm">Loading GPU status…</p>
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card padding="md" variant="bordered">
        <CardContent className="flex items-center gap-2 text-amber-400 text-sm">
          <AlertTriangle className="w-4 h-4" />
          GPU status unavailable - backend may still be starting up.
        </CardContent>
      </Card>
    );
  }

  const { device, metrics, health } = data;
  const backendLabel = device.is_rocm ? "AMD ROCm" : device.is_cuda ? "NVIDIA CUDA" : "CPU";

  return (
    <Card variant="glass" padding="md" glow={device.backend === "cpu" ? "none" : "teal"}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Cpu className="w-4 h-4" />
          Compute Backend
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-white/50 text-sm">Backend</span>
          <Badge variant={device.backend === "cpu" ? "outline" : "success"}>{backendLabel}</Badge>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-white/50 text-sm">Device</span>
          <span className="text-white/80 text-sm">{device.device_name}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-white/50 text-sm">Health</span>
          <Badge variant={health.healthy ? "success" : "danger"} dot>
            {health.healthy ? "Healthy" : "Unhealthy"}
          </Badge>
        </div>
        {typeof metrics.gpu_utilization_pct === "number" && (
          <div className="flex items-center justify-between">
            <span className="text-white/50 text-sm flex items-center gap-1">
              <Activity className="w-3.5 h-3.5" /> Utilization
            </span>
            <span className="text-white/80 text-sm">{metrics.gpu_utilization_pct as number}%</span>
          </div>
        )}
        {typeof metrics.memory_used_mb === "number" && typeof metrics.memory_total_mb === "number" && (
          <div className="flex items-center justify-between">
            <span className="text-white/50 text-sm flex items-center gap-1">
              <Zap className="w-3.5 h-3.5" /> VRAM
            </span>
            <span className="text-white/80 text-sm">
              {Math.round(metrics.memory_used_mb as number)} / {Math.round(metrics.memory_total_mb as number)} MB
            </span>
          </div>
        )}
        {metrics.note && <p className="text-white/30 text-xs pt-1">{metrics.note as string}</p>}
        <p className="text-white/30 text-xs">{health.reason}</p>
      </CardContent>
    </Card>
  );
}
