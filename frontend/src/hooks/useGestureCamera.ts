"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useConsultationStore } from "@/store/consultation";
import type { GestureResult } from "@/types";

interface UseGestureCameraOptions {
  enabled: boolean;
  consultationId: string | null;
  userId: string;
  userRole: string;
  /** Called with gesture result after each processed frame */
  onGestureResult?: (result: GestureResult) => void;
  /** Emit frame via Socket.IO — provided by the consultation socket hook */
  emitFrame?: (frameB64: string, consultationId: string) => void;
  /** Frame rate — default 10fps to balance accuracy vs bandwidth */
  fps?: number;
}

export function useGestureCamera({
  enabled,
  consultationId,
  userId: _userId,
  userRole: _userRole,
  onGestureResult,
  emitFrame,
  fps = 10,
}: UseGestureCameraOptions) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { setLastGesture } = useConsultationStore();

  // Create offscreen canvas for frame capture
  useEffect(() => {
    canvasRef.current = document.createElement("canvas");
    canvasRef.current.width = 320;
    canvasRef.current.height = 240;
  }, []);

  const captureAndEmit = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2 || !consultationId || !emitFrame) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Mirror the frame (consistent with MediaPipe expectation)
    ctx.save();
    ctx.scale(-1, 1);
    ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
    ctx.restore();

    // Convert to base64 JPEG at quality 0.7 — balance quality vs bandwidth
    const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
    const base64 = dataUrl.split(",")[1];
    if (base64) {
      emitFrame(base64, consultationId);
    }
  }, [consultationId, emitFrame]);

  const startCapture = useCallback(async () => {
    if (!enabled || isCapturing) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setIsCapturing(true);
      setError(null);

      // Start frame capture interval
      const intervalMs = Math.round(1000 / fps);
      intervalRef.current = setInterval(captureAndEmit, intervalMs);
    } catch (err: unknown) {
      const message = (err as Error).message || "Camera access denied";
      setError(message);
    }
  }, [enabled, isCapturing, fps, captureAndEmit]);

  const stopCapture = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCapturing(false);
  }, []);

  // Auto-start/stop based on enabled prop
  useEffect(() => {
    if (enabled) {
      startCapture();
    } else {
      stopCapture();
    }
    return () => stopCapture();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  // Handle incoming gesture result from socket
  const handleGestureResult = useCallback(
    (result: GestureResult) => {
      setLastGesture(result);
      onGestureResult?.(result);
    },
    [setLastGesture, onGestureResult]
  );

  return {
    videoRef,
    isCapturing,
    error,
    startCapture,
    stopCapture,
    handleGestureResult,
  };
}
