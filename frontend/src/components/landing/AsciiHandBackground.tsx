"use client";

import { useEffect, useRef } from "react";

/**
 * ASCII hand canvas effect — ported from the reference "hand gsap" prototype.
 * Two hand images are sampled into a low-res brightness grid, then redrawn as
 * monospace ASCII glyphs on canvas. Cursor proximity lights up a small
 * cluster of neighbouring glyphs, and each hand drifts slightly with the
 * mouse for a subtle parallax feel. Same core algorithm as the reference
 * script.js, adapted to a self-contained React effect (no GSAP/ScrollTrigger
 * needed here since the hero is always visible, not scroll-revealed).
 */

const ASCII_CHARS = "... ... .. :::=+xX#0369";
const FONT_SIZE = 18;
const CELL_SIZE = 20;
const ASCII_COLUMNS = 80;

const CHAR_COLOR = "#274b7a";
const HOVER_COLOR = "#60A5FA";
const HOVER_CHAR_COLOR = "#060608";

const HOVER_RADIUS = 8;
const CLUSTER_SIZE = 10;
const HIGHLIGHT_LIFETIME = 300;

const PARALLAX_STRENGTH = 14;
const PARALLAX_EASE = 0.06;

const backgroundCharIndex = ASCII_CHARS.lastIndexOf(".");

interface Cell {
  col: number;
  row: number;
  char: string;
  highlightEndTime: number;
}

interface HandInstance {
  canvas: HTMLCanvasElement;
  cells: Map<string, Cell>;
  cellList: Cell[];
  rows: number;
}

export default function AsciiHandBackground() {
  const containerRef = useRef<HTMLDivElement>(null);
  const leftImgRef = useRef<HTMLImageElement>(null);
  const rightImgRef = useRef<HTMLImageElement>(null);
  const leftWrapRef = useRef<HTMLDivElement>(null);
  const rightWrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const hands: HandInstance[] = [];
    const cancelRenders: Array<() => void> = [];
    let parallaxFrame = 0;

    const sampleImagePixels = (image: HTMLImageElement, gridRows: number) => {
      const sampleCanvas = document.createElement("canvas");
      sampleCanvas.width = ASCII_COLUMNS;
      sampleCanvas.height = gridRows;
      const sampleCtx = sampleCanvas.getContext("2d")!;
      sampleCtx.drawImage(image, 0, 0, ASCII_COLUMNS, gridRows);
      return sampleCtx.getImageData(0, 0, ASCII_COLUMNS, gridRows).data;
    };

    const pixelToCharIndex = (pixels: Uint8ClampedArray, pixelOffset: number) => {
      const brightness =
        (pixels[pixelOffset] * 0.299 +
          pixels[pixelOffset + 1] * 0.587 +
          pixels[pixelOffset + 2] * 0.114) /
        255;
      return Math.min(
        ASCII_CHARS.length - 1,
        Math.floor((1 - brightness) * ASCII_CHARS.length)
      );
    };

    const buildCells = (image: HTMLImageElement) => {
      const rows = Math.round(ASCII_COLUMNS / (image.naturalWidth / image.naturalHeight));
      const pixels = sampleImagePixels(image, rows);
      const cells = new Map<string, Cell>();

      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < ASCII_COLUMNS; col++) {
          const charIndex = pixelToCharIndex(pixels, (row * ASCII_COLUMNS + col) * 4);
          if (charIndex <= backgroundCharIndex) continue;
          cells.set(`${col},${row}`, {
            col,
            row,
            char: ASCII_CHARS[charIndex],
            highlightEndTime: 0,
          });
        }
      }
      return { rows, cells };
    };

    const setupHand = (image: HTMLImageElement, wrapper: HTMLDivElement): HandInstance => {
      const { rows, cells } = buildCells(image);
      const cellList = [...cells.values()];

      const canvas = document.createElement("canvas");
      canvas.style.position = "absolute";
      canvas.style.inset = "0";
      canvas.style.width = "100%";
      canvas.style.height = "100%";
      wrapper.appendChild(canvas);

      canvas.width = ASCII_COLUMNS * CELL_SIZE * dpr;
      canvas.height = rows * CELL_SIZE * dpr;

      const ctx = canvas.getContext("2d")!;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.font = `${FONT_SIZE}px monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";

      const metrics = ctx.measureText("X");
      const glyphHeight = metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent;
      const baseLineOffset = CELL_SIZE / 2 + glyphHeight / 2 - metrics.actualBoundingBoxDescent;

      const canvasWidth = ASCII_COLUMNS * CELL_SIZE;
      const canvasHeight = rows * CELL_SIZE;

      let frameId = 0;
      const render = () => {
        const now = Date.now();
        ctx.clearRect(0, 0, canvasWidth, canvasHeight);

        for (const cell of cellList) {
          const x = cell.col * CELL_SIZE;
          const y = cell.row * CELL_SIZE;
          const isHighlighted = cell.highlightEndTime > now;

          if (isHighlighted) {
            ctx.fillStyle = HOVER_COLOR;
            ctx.fillRect(x, y, CELL_SIZE, CELL_SIZE);
          }
          ctx.fillStyle = isHighlighted ? HOVER_CHAR_COLOR : CHAR_COLOR;
          ctx.fillText(cell.char, x + CELL_SIZE / 2, y + baseLineOffset);
        }
        frameId = requestAnimationFrame(render);
      };
      render();
      cancelRenders.push(() => cancelAnimationFrame(frameId));

      return { canvas, cells, cellList, rows };
    };

    const initHand = (imgEl: HTMLImageElement | null, wrapEl: HTMLDivElement | null) => {
      if (!imgEl || !wrapEl) return;
      const start = () => hands.push(setupHand(imgEl, wrapEl));
      if (imgEl.complete && imgEl.naturalHeight) start();
      else imgEl.addEventListener("load", start, { once: true });
    };

    initHand(leftImgRef.current, leftWrapRef.current);
    initHand(rightImgRef.current, rightWrapRef.current);

    const highlightCluster = (cells: Map<string, Cell>, startCell: Cell) => {
      const now = Date.now();
      startCell.highlightEndTime = now + HIGHLIGHT_LIFETIME;

      const steps = Math.floor(Math.random() * CLUSTER_SIZE) + 1;
      const litCells = [startCell];
      let current = startCell;

      for (let step = 0; step < steps; step++) {
        const neighbours: Cell[] = [];
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue;
            const neighbour = cells.get(`${current.col + dx},${current.row + dy}`);
            if (neighbour && !litCells.includes(neighbour)) neighbours.push(neighbour);
          }
        }
        if (neighbours.length === 0) break;

        const next = neighbours[Math.floor(Math.random() * neighbours.length)];
        next.highlightEndTime = now + HIGHLIGHT_LIFETIME + step * 10;
        litCells.push(next);
        current = next;
      }
    };

    const hoverHand = (hand: HandInstance, clientX: number, clientY: number) => {
      const rect = hand.canvas.getBoundingClientRect();
      const mouseCol = ((clientX - rect.left) / rect.width) * ASCII_COLUMNS;
      const mouseRow = ((clientY - rect.top) / rect.height) * hand.rows;

      let closest: Cell | null = null;
      let closestDist = Infinity;
      for (const cell of hand.cellList) {
        const dx = mouseCol - cell.col;
        const dy = mouseRow - cell.row;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < closestDist) {
          closestDist = dist;
          closest = cell;
        }
      }
      if (closest && closestDist <= HOVER_RADIUS) {
        highlightCluster(hand.cells, closest);
      }
    };

    const handleHoverMove = (event: MouseEvent) => {
      hands.forEach((hand) => hoverHand(hand, event.clientX, event.clientY));
    };
    window.addEventListener("mousemove", handleHoverMove);

    // Gentle parallax drift toward the cursor, mirroring the reference footer effect
    const pointer = { x: 0, y: 0 };
    const drift = { x: 0, y: 0 };
    const wrappers = [leftWrapRef.current, rightWrapRef.current].filter(
      (el): el is HTMLDivElement => el !== null
    );

    const setPointerTarget = (clientX: number, clientY: number) => {
      const rect = container.getBoundingClientRect();
      pointer.x = ((clientX - rect.left) / rect.width - 0.5) * PARALLAX_STRENGTH * 2;
      pointer.y = ((clientY - rect.top) / rect.height - 0.5) * PARALLAX_STRENGTH * 2;
    };

    const renderParallax = () => {
      drift.x += (pointer.x - drift.x) * PARALLAX_EASE;
      drift.y += (pointer.y - drift.y) * PARALLAX_EASE;

      wrappers.forEach((wrapper, i) => {
        const direction = i === 0 ? 1 : -1;
        const x = drift.x * direction;
        const y = -drift.y;
        wrapper.style.transform = `translateY(-50%) translate(${x}px, ${y}px)`;
      });
      parallaxFrame = requestAnimationFrame(renderParallax);
    };
    renderParallax();

    const handlePointerMove = (event: MouseEvent) => setPointerTarget(event.clientX, event.clientY);
    window.addEventListener("mousemove", handlePointerMove);

    return () => {
      window.removeEventListener("mousemove", handleHoverMove);
      window.removeEventListener("mousemove", handlePointerMove);
      cancelAnimationFrame(parallaxFrame);
      cancelRenders.forEach((cancel) => cancel());
    };
  }, []);

  return (
    <div ref={containerRef} className="absolute inset-0 overflow-hidden pointer-events-none">
      <div
        ref={leftWrapRef}
        className="absolute left-[-6%] top-1/2 -translate-y-1/2 w-[42%] min-w-[220px] opacity-60"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img ref={leftImgRef} src="/hand-left.jpg" alt="" className="w-full block opacity-0" />
      </div>
      <div
        ref={rightWrapRef}
        className="absolute right-[-6%] top-1/2 -translate-y-1/2 w-[42%] min-w-[220px] opacity-60"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img ref={rightImgRef} src="/hand-right.jpg" alt="" className="w-full block opacity-0" />
      </div>
    </div>
  );
}
