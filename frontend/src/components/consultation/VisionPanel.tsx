"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Camera, CameraOff, HeartPulse, Activity } from "lucide-react";
import { videoApi } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface VisionSummary {
  pain_score: number;
  body_part: string | null;
  confidence: number;
  distress_flags: string[];
  primary_gesture: string | null;
  emotion: string | null;
  posture: string | null;
  movement: string | null;
  speech_emotion: string | null;
}

const FRAME_INTERVAL_MS = 1500;

interface VisionPanelProps {
  consultationId: string;
}

export function VisionPanel({ consultationId }: VisionPanelProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [active, setActive] = useState(false);
  const [summary, setSummary] = useState<VisionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const captureAndSend = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      async (blob) => {
        if (!blob) return;
        try {
          const { data } = await videoApi.sendFrame(consultationId, blob);
          setSummary(data.summary ?? null);
          setError(null);
        } catch {
          setError("Vision analysis temporarily unavailable");
        }
      },
      "image/jpeg",
      0.7
    );
  }, [consultationId]);

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 480, height: 360 } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      await videoApi.start(consultationId);
      intervalRef.current = setInterval(captureAndSend, FRAME_INTERVAL_MS);
      setActive(true);
      setError(null);
    } catch {
      setError("Camera access denied or unavailable");
    }
  }, [consultationId, captureAndSend]);

  const stop = useCallback(async () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setActive(false);
    setSummary(null);
    try {
      await videoApi.stop(consultationId);
    } catch {
      // best-effort - session cleanup on the backend also self-expires via idle timeout
    }
  }, [consultationId]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return (
    <Card variant="glass" padding="md">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-base">
          <HeartPulse className="w-4 h-4" />
          Vision Observations
        </CardTitle>
        <Button size="sm" variant={active ? "secondary" : "primary"} onClick={active ? stop : start}>
          {active ? (
            <>
              <CameraOff className="w-4 h-4 mr-1.5" /> Stop
            </>
          ) : (
            <>
              <Camera className="w-4 h-4 mr-1.5" /> Start
            </>
          )}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <video ref={videoRef} muted playsInline className={active ? "w-full rounded-lg bg-black" : "hidden"} />
        <canvas ref={canvasRef} className="hidden" />

        {error && <p className="text-amber-400 text-xs">{error}</p>}

        {!active && !error && (
          <p className="text-white/40 text-sm">
            Start the camera to let the vision pipeline detect pain, posture, and distress signals in real time.
          </p>
        )}

        {summary && (
          <div className="space-y-2 pt-1">
            <div className="flex items-center justify-between">
              <span className="text-white/50 text-sm flex items-center gap-1">
                <Activity className="w-3.5 h-3.5" /> Pain score
              </span>
              <Badge variant={summary.pain_score > 0.6 ? "danger" : summary.pain_score > 0.3 ? "warning" : "default"}>
                {(summary.pain_score * 100).toFixed(0)}%{summary.body_part ? ` · ${summary.body_part}` : ""}
              </Badge>
            </div>
            {summary.emotion && (
              <div className="flex items-center justify-between">
                <span className="text-white/50 text-sm">Emotion</span>
                <span className="text-white/80 text-sm">{summary.emotion.replace(/_/g, " ")}</span>
              </div>
            )}
            {summary.posture && (
              <div className="flex items-center justify-between">
                <span className="text-white/50 text-sm">Posture</span>
                <span className="text-white/80 text-sm">{summary.posture.replace(/_/g, " ")}</span>
              </div>
            )}
            {summary.distress_flags?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {summary.distress_flags.map((flag) => (
                  <Badge key={flag} variant="danger" size="sm">
                    {flag.replace(/_/g, " ")}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
