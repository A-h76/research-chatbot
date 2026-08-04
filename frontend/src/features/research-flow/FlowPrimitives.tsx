import { forwardRef, useRef, type ReactNode } from "react";
import { AnimatedBeam } from "@/components/ui/animated-beam";
import { cn } from "@/lib/utils";

/** Shared node chip for Research OS beam diagrams. */
export const FlowNode = forwardRef<
  HTMLDivElement,
  {
    label: string;
    sub?: string;
    active?: boolean;
    done?: boolean;
    className?: string;
    children?: ReactNode;
  }
>(function FlowNode({ label, sub, active, done, className, children }, ref) {
  return (
    <div
      ref={ref}
      className={cn(
        "relative z-10 flex min-w-[5.5rem] max-w-[8.5rem] flex-col items-center justify-center rounded-xl border bg-card px-2.5 py-2 text-center shadow-sm",
        active && "border-primary/50 bg-primary/5 ring-1 ring-primary/25",
        done && !active && "border-primary/30",
        !active && !done && "border-border",
        className,
      )}
    >
      {children}
      <span className="text-[11px] font-semibold leading-tight tracking-tight text-foreground">{label}</span>
      {sub ? <span className="mt-0.5 text-[9px] leading-tight text-muted-foreground">{sub}</span> : null}
    </div>
  );
});

type BeamLink = {
  from: React.RefObject<HTMLElement | null>;
  to: React.RefObject<HTMLElement | null>;
  delay?: number;
  reverse?: boolean;
  curvature?: number;
};

export function BeamCanvas({
  className,
  children,
  beams,
}: {
  className?: string;
  children: ReactNode;
  beams: BeamLink[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {children}
      {beams.map((b, i) => (
        <AnimatedBeam
          key={i}
          containerRef={containerRef}
          fromRef={b.from}
          toRef={b.to}
          delay={b.delay ?? i * 0.35}
          duration={4.5}
          reverse={b.reverse}
          curvature={b.curvature ?? 0}
        />
      ))}
    </div>
  );
}
