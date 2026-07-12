"use client";

import { useEffect, useRef } from "react";

// MediaPipe hand connections as index pairs
const HAND_CONNECTIONS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4],           // thumb
  [0, 5], [5, 6], [6, 7], [7, 8],           // index
  [5, 9], [9, 10], [10, 11], [11, 12],      // middle
  [9, 13], [13, 14], [14, 15], [15, 16],    // ring
  [13, 17], [17, 18], [18, 19], [19, 20],   // pinky
  [0, 17],                                   // palm base
];

interface Landmark {
  x: number;
  y: number;
  z: number;
}

interface HandLandmarkRendererProps {
  landmarks: Landmark[][] | null | undefined;
  width: number;
  height: number;
  /** Color for skeleton lines. Defaults to blue for patient, teal for doctor */
  color?: string;
  className?: string;
}

export function HandLandmarkRenderer({
  landmarks,
  width,
  height,
  color = "#60A5FA",
  className,
}: HandLandmarkRendererProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!landmarks || landmarks.length === 0) return;

    for (const hand of landmarks) {
      if (!hand || hand.length < 21) continue;

      // Convert normalized coords to pixel coords
      const pts = hand.map((lm) => ({
        x: lm.x * canvas.width,
        y: lm.y * canvas.height,
      }));

      // Draw connections
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.7;

      for (const [start, end] of HAND_CONNECTIONS) {
        if (!pts[start] || !pts[end]) continue;
        ctx.beginPath();
        ctx.moveTo(pts[start].x, pts[start].y);
        ctx.lineTo(pts[end].x, pts[end].y);
        ctx.stroke();
      }

      // Draw landmark dots
      ctx.globalAlpha = 1;
      for (let i = 0; i < pts.length; i++) {
        const pt = pts[i];
        // Fingertips (4, 8, 12, 16, 20) are larger
        const isTip = [4, 8, 12, 16, 20].includes(i);
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, isTip ? 4 : 2.5, 0, Math.PI * 2);
        ctx.fillStyle = isTip ? "#FFFFFF" : color;
        ctx.fill();
      }
    }

    ctx.globalAlpha = 1;
  }, [landmarks, color, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className={className}
      style={{ pointerEvents: "none" }}
    />
  );
}
