"use client";

import { useRef, useCallback, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Annotation } from "@/types";

interface AnnotationLayerProps {
  annotations: Annotation[];
  drawMode: boolean;
  isDoctor: boolean;
  containerWidth: number;
  containerHeight: number;
  onAddAnnotation: (annotation: Omit<Annotation, "created_by" | "role" | "timestamp">) => void;
  onRemoveAnnotation: (id: string) => void;
  onClearAnnotations: () => void;
  className?: string;
}

export function AnnotationLayer({
  annotations,
  drawMode,
  isDoctor,
  containerWidth,
  containerHeight,
  onAddAnnotation,
  onRemoveAnnotation,
  onClearAnnotations,
  className,
}: AnnotationLayerProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const isDrawing = useRef(false);
  const currentPath = useRef<{ x: number; y: number }[]>([]);
  const [drawingPath, setDrawingPath] = useState<string>("");
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const getRelativeCoords = useCallback(
    (e: React.MouseEvent | React.TouchEvent) => {
      const svg = svgRef.current;
      if (!svg) return { x: 0, y: 0 };
      const rect = svg.getBoundingClientRect();
      const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
      const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
      return {
        x: (clientX - rect.left) / rect.width,
        y: (clientY - rect.top) / rect.height,
      };
    },
    []
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!drawMode || !isDoctor) return;
      isDrawing.current = true;
      const coords = getRelativeCoords(e);
      currentPath.current = [coords];
      setDrawingPath(`M ${coords.x * containerWidth} ${coords.y * containerHeight}`);
    },
    [drawMode, isDoctor, getRelativeCoords, containerWidth, containerHeight]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDrawing.current) return;
      const coords = getRelativeCoords(e);
      currentPath.current.push(coords);
      const last = currentPath.current[currentPath.current.length - 2];
      if (last) {
        setDrawingPath((prev) =>
          `${prev} L ${coords.x * containerWidth} ${coords.y * containerHeight}`
        );
      }
    },
    [getRelativeCoords, containerWidth, containerHeight]
  );

  const handleMouseUp = useCallback(
    (e: React.MouseEvent) => {
      if (!isDrawing.current) return;
      isDrawing.current = false;
      setDrawingPath("");

      if (currentPath.current.length < 2) {
        // Single click = point annotation
        const coords = getRelativeCoords(e);
        onAddAnnotation({
          id: `ann_${Date.now()}`,
          type: "point",
          coordinates: { x: coords.x, y: coords.y, radius: 18 },
          body_region: detectBodyRegion(coords.y),
          color: "#FF6B6B",
        });
      } else {
        // Drawing = region annotation (use centroid)
        const xs = currentPath.current.map((p) => p.x);
        const ys = currentPath.current.map((p) => p.y);
        const cx = xs.reduce((a, b) => a + b, 0) / xs.length;
        const cy = ys.reduce((a, b) => a + b, 0) / ys.length;
        onAddAnnotation({
          id: `ann_${Date.now()}`,
          type: "drawing",
          coordinates: { x: cx, y: cy, radius: 15 },
          body_region: detectBodyRegion(cy),
          color: "#FF6B6B",
        });
      }
      currentPath.current = [];
    },
    [getRelativeCoords, onAddAnnotation]
  );

  return (
    <>
      {isDoctor && annotations.length > 0 && (
        <button
          type="button"
          onClick={onClearAnnotations}
          className="absolute top-3 right-3 z-20 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-black/50 hover:bg-black/70 border border-white/10 text-white/70 hover:text-white text-xs transition-colors pointer-events-auto"
          title="Clear all annotations"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Clear all
        </button>
      )}
      <svg
        ref={svgRef}
        className={cn(
          "absolute inset-0 w-full h-full",
          drawMode && isDoctor ? "cursor-crosshair" : "pointer-events-none",
          className
        )}
        viewBox={`0 0 ${containerWidth} ${containerHeight}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      onMouseLeave={() => {
        isDrawing.current = false;
        setDrawingPath("");
        currentPath.current = [];
      }}
    >
      {/* Existing annotations */}
      <AnimatePresence>
        {annotations.map((ann) => {
          const px = ann.coordinates.x * containerWidth;
          const py = ann.coordinates.y * containerHeight;
          const r = ann.coordinates.radius ?? 18;

          return (
            <g
              key={ann.id}
              style={{ pointerEvents: isDoctor ? "auto" : "none" }}
              onMouseEnter={() => setHoveredId(ann.id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              {/* Pulsing ring */}
              <circle
                cx={px}
                cy={py}
                r={r + 6}
                fill="none"
                stroke={ann.color}
                strokeWidth={1}
                opacity={0.3}
                style={{ animation: "pulse 2s infinite" }}
              />
              {/* Main circle */}
              <circle
                cx={px}
                cy={py}
                r={r}
                fill={ann.color + "22"}
                stroke={ann.color}
                strokeWidth={1.5}
              />
              {/* Label */}
              {ann.body_region && (
                <text
                  x={px + r + 6}
                  y={py + 4}
                  fill={ann.color}
                  fontSize={11}
                  fontFamily="monospace"
                  style={{ userSelect: "none" }}
                >
                  {ann.body_region}
                </text>
              )}
              {/* Delete button on hover */}
              {hoveredId === ann.id && isDoctor && (
                <g
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveAnnotation(ann.id);
                  }}
                  style={{ cursor: "pointer" }}
                >
                  <circle cx={px + r - 2} cy={py - r + 2} r={8} fill="#EF4444" opacity={0.9} />
                  <text x={px + r - 2} y={py - r + 6} textAnchor="middle" fill="white" fontSize={10} fontWeight="bold">
                    ×
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </AnimatePresence>

      {/* Live drawing path */}
      {drawingPath && (
        <path
          d={drawingPath}
          fill="none"
          stroke="#FF6B6B"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.8}
        />
      )}
      </svg>
    </>
  );
}

/** Simple heuristic body region from Y coordinate (normalized 0–1) */
function detectBodyRegion(y: number): string {
  if (y < 0.15) return "Head";
  if (y < 0.22) return "Neck";
  if (y < 0.38) return "Chest";
  if (y < 0.55) return "Abdomen";
  if (y < 0.68) return "Pelvis";
  if (y < 0.85) return "Leg";
  return "Foot";
}
