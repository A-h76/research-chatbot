import { useEffect, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { renderToString } from "react-dom/server";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Icon {
  x: number;
  y: number;
  z: number;
  scale: number;
  opacity: number;
  id: number;
}

interface IconCloudProps {
  icons?: React.ReactNode[];
  images?: string[];
  /** Play/pause control — off by default (hover-to-spin is enough). */
  showControl?: boolean;
  /** When true (default), sphere is static until pointer hovers. */
  animateOnHover?: boolean;
  className?: string;
  width?: number;
  height?: number;
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

const ICON_SIZE = 48;
const ICON_RADIUS = ICON_SIZE / 2;

/**
 * Magic UI Icon Cloud — interactive 3D tag cloud.
 * Prefer `images` for brand marks. Default: static until hover, no play/pause chrome.
 */
export function IconCloud({
  icons,
  images,
  showControl = false,
  animateOnHover = true,
  className,
  width = 420,
  height = 420,
}: IconCloudProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [iconPositions, setIconPositions] = useState<Icon[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [lastMousePos, setLastMousePos] = useState({ x: 0, y: 0 });
  const [mousePos, setMousePos] = useState({ x: width / 2, y: height / 2 });
  const [targetRotation, setTargetRotation] = useState<{
    x: number;
    y: number;
    startX: number;
    startY: number;
    distance: number;
    startTime: number;
    duration: number;
  } | null>(null);
  const animationFrameRef = useRef<number>(0);
  const rotationRef = useRef({ x: 0.15, y: 0.35 });
  const iconCanvasesRef = useRef<HTMLCanvasElement[]>([]);
  const imagesLoadedRef = useRef<boolean[]>([]);
  const reducedMotionRef = useRef(false);
  const [, setAssetsVersion] = useState(0);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    reducedMotionRef.current = mediaQuery.matches;
    if (mediaQuery.matches) setIsPaused(true);

    const handleChange = (e: MediaQueryListEvent) => {
      reducedMotionRef.current = e.matches;
      setIsPaused(e.matches);
    };
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    if (!icons && !images) return;

    const items = icons ?? images ?? [];
    imagesLoadedRef.current = new Array(items.length).fill(false);

    const markLoaded = (index: number) => {
      imagesLoadedRef.current[index] = true;
      setAssetsVersion((v) => v + 1);
    };

    const newIconCanvases = items.map((item, index) => {
      const offscreen = document.createElement("canvas");
      offscreen.width = ICON_SIZE;
      offscreen.height = ICON_SIZE;
      const offCtx = offscreen.getContext("2d");

      if (offCtx) {
        if (images) {
          const img = new Image();
          img.crossOrigin = "anonymous";
          img.src = items[index] as string;
          img.onload = () => {
            offCtx.clearRect(0, 0, ICON_SIZE, ICON_SIZE);
            offCtx.beginPath();
            offCtx.arc(ICON_RADIUS, ICON_RADIUS, ICON_RADIUS, 0, Math.PI * 2);
            offCtx.closePath();
            offCtx.clip();
            offCtx.fillStyle = "#ffffff";
            offCtx.fillRect(0, 0, ICON_SIZE, ICON_SIZE);
            const pad = 8;
            offCtx.drawImage(img, pad, pad, ICON_SIZE - pad * 2, ICON_SIZE - pad * 2);
            markLoaded(index);
          };
        } else {
          offCtx.scale(0.48, 0.48);
          const svgString = renderToString(item as React.ReactElement);
          const img = new Image();
          img.src = "data:image/svg+xml;base64," + btoa(svgString);
          img.onload = () => {
            offCtx.clearRect(0, 0, ICON_SIZE, ICON_SIZE);
            offCtx.drawImage(img, 0, 0);
            markLoaded(index);
          };
        }
      }
      return offscreen;
    });

    iconCanvasesRef.current = newIconCanvases;
  }, [icons, images]);

  useEffect(() => {
    const items = icons ?? images ?? [];
    const newIcons: Icon[] = [];
    const numIcons = items.length || 20;
    const offset = 2 / numIcons;
    const increment = Math.PI * (3 - Math.sqrt(5));
    // Slightly denser sphere than Magic UI default (closer to demo look)
    const radius = 110;

    for (let i = 0; i < numIcons; i++) {
      const y = i * offset - 1 + offset / 2;
      const r = Math.sqrt(1 - y * y);
      const phi = i * increment;
      const x = Math.cos(phi) * r;
      const z = Math.sin(phi) * r;
      newIcons.push({
        x: x * radius,
        y: y * radius,
        z: z * radius,
        scale: 1,
        opacity: 1,
        id: i,
      });
    }
    setIconPositions(newIcons);
  }, [icons, images]);

  const canAutoRotate =
    !isPaused &&
    !reducedMotionRef.current &&
    (!animateOnHover || isHovering);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect || !canvasRef.current) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const ctx = canvasRef.current.getContext("2d");
    if (!ctx) return;

    iconPositions.forEach((icon) => {
      const cosX = Math.cos(rotationRef.current.x);
      const sinX = Math.sin(rotationRef.current.x);
      const cosY = Math.cos(rotationRef.current.y);
      const sinY = Math.sin(rotationRef.current.y);

      const rotatedX = icon.x * cosY - icon.z * sinY;
      const rotatedZ = icon.x * sinY + icon.z * cosY;
      const rotatedY = icon.y * cosX + rotatedZ * sinX;

      const screenX = canvasRef.current!.width / 2 + rotatedX;
      const screenY = canvasRef.current!.height / 2 + rotatedY;
      const scale = (rotatedZ + 200) / 300;
      const radius = ICON_RADIUS * scale;
      const dx = x - screenX;
      const dy = y - screenY;

      if (dx * dx + dy * dy < radius * radius) {
        const targetX = -Math.atan2(icon.y, Math.sqrt(icon.x * icon.x + icon.z * icon.z));
        const targetY = Math.atan2(icon.x, icon.z);
        const currentX = rotationRef.current.x;
        const currentY = rotationRef.current.y;
        const distance = Math.sqrt(
          Math.pow(targetX - currentX, 2) + Math.pow(targetY - currentY, 2),
        );
        const duration = Math.min(2000, Math.max(800, distance * 1000));
        setTargetRotation({
          x: targetX,
          y: targetY,
          startX: currentX,
          startY: currentY,
          distance,
          startTime: performance.now(),
          duration,
        });
        return;
      }
    });

    setIsDragging(true);
    setLastMousePos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    }
    if (isDragging) {
      const deltaX = e.clientX - lastMousePos.x;
      const deltaY = e.clientY - lastMousePos.y;
      rotationRef.current = {
        x: rotationRef.current.x + deltaY * 0.002,
        y: rotationRef.current.y + deltaX * 0.002,
      };
      setLastMousePos({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const maxDistance = Math.sqrt(centerX * centerX + centerY * centerY);
      const dx = mousePos.x - centerX;
      const dy = mousePos.y - centerY;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const speed = 0.003 + (distance / maxDistance) * 0.01;

      if (targetRotation) {
        const elapsed = performance.now() - targetRotation.startTime;
        const progress = Math.min(1, elapsed / targetRotation.duration);
        const easedProgress = easeOutCubic(progress);
        rotationRef.current = {
          x:
            targetRotation.startX +
            (targetRotation.x - targetRotation.startX) * easedProgress,
          y:
            targetRotation.startY +
            (targetRotation.y - targetRotation.startY) * easedProgress,
        };
        if (progress >= 1) setTargetRotation(null);
      } else if (!isDragging && canAutoRotate) {
        rotationRef.current = {
          x: rotationRef.current.x + (dy / canvas.height) * speed,
          y: rotationRef.current.y + (dx / canvas.width) * speed,
        };
      }

      // Draw back-to-front for denser Magic UI look
      const drawn = iconPositions.map((icon, index) => {
        const cosX = Math.cos(rotationRef.current.x);
        const sinX = Math.sin(rotationRef.current.x);
        const cosY = Math.cos(rotationRef.current.y);
        const sinY = Math.sin(rotationRef.current.y);
        const rotatedX = icon.x * cosY - icon.z * sinY;
        const rotatedZ = icon.x * sinY + icon.z * cosY;
        const rotatedY = icon.y * cosX + rotatedZ * sinX;
        return { icon, index, rotatedX, rotatedY, rotatedZ };
      });
      drawn.sort((a, b) => a.rotatedZ - b.rotatedZ);

      drawn.forEach(({ icon, index, rotatedX, rotatedY, rotatedZ }) => {
        const scale = (rotatedZ + 200) / 300;
        const opacity = Math.max(0.25, Math.min(1, (rotatedZ + 150) / 200));

        ctx.save();
        ctx.translate(canvas.width / 2 + rotatedX, canvas.height / 2 + rotatedY);
        ctx.scale(scale, scale);
        ctx.globalAlpha = opacity;

        if (icons || images) {
          if (iconCanvasesRef.current[index] && imagesLoadedRef.current[index]) {
            ctx.drawImage(
              iconCanvasesRef.current[index],
              -ICON_RADIUS,
              -ICON_RADIUS,
              ICON_SIZE,
              ICON_SIZE,
            );
          }
        } else {
          ctx.beginPath();
          ctx.arc(0, 0, ICON_RADIUS, 0, Math.PI * 2);
          ctx.fillStyle = "#0F6E6A";
          ctx.fill();
          ctx.fillStyle = "white";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.font = "16px Arial";
          ctx.fillText(`${icon.id + 1}`, 0, 0);
        }
        ctx.restore();
      });

      const hasPendingAssets =
        Boolean(icons || images) && !imagesLoadedRef.current.every((loaded) => loaded);
      const shouldContinue =
        canAutoRotate ||
        isDragging ||
        targetRotation !== null ||
        hasPendingAssets ||
        isHovering;

      if (shouldContinue || hasPendingAssets) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        // One more idle frame is already drawn; stop until hover resumes.
        animationFrameRef.current = 0;
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [
    icons,
    images,
    iconPositions,
    isDragging,
    isPaused,
    isHovering,
    canAutoRotate,
    mousePos,
    targetRotation,
  ]);

  return (
    <div className={cn("relative inline-block", className)}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => {
          setIsHovering(false);
          handleMouseUp();
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        className="cursor-grab rounded-lg active:cursor-grabbing"
        aria-label="Interactive 3D research ecosystem cloud — hover to spin"
        role="img"
      />
      {showControl && (
        <Button
          variant="outline"
          size="icon"
          onClick={() => setIsPaused(!isPaused)}
          aria-label={isPaused ? "Play Animation" : "Pause Animation"}
          className="absolute top-2 right-2 size-8"
        >
          {isPaused ? <Play size={16} /> : <Pause size={16} />}
        </Button>
      )}
    </div>
  );
}
