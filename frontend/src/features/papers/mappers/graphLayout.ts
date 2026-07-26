/**
 * Deterministic force-ish layout for knowledge graph nodes.
 * Runs once per filtered node/edge set — no animation loop in React.
 */

import type { GraphEdgeView, GraphNodeView } from "./graph";

export type GraphPoint = { x: number; y: number };

export type GraphLayout = {
  positions: Record<string, GraphPoint>;
  width: number;
  height: number;
};

function hashSeed(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967296;
}

/**
 * Layout nodes in a circle seeded by id, then relax with a few force iterations.
 */
export function layoutKnowledgeGraph(
  nodes: GraphNodeView[],
  edges: GraphEdgeView[],
  opts?: { width?: number; height?: number; iterations?: number },
): GraphLayout {
  const width = opts?.width ?? 720;
  const height = opts?.height ?? 480;
  const iterations = opts?.iterations ?? 48;
  const positions: Record<string, GraphPoint> = {};

  if (nodes.length === 0) {
    return { positions, width, height };
  }

  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.36;

  nodes.forEach((n, i) => {
    const angle = (i / nodes.length) * Math.PI * 2 + hashSeed(n.id) * 0.2;
    const jitter = 8 + hashSeed(n.label) * 12;
    positions[n.id] = {
      x: cx + Math.cos(angle) * (radius + jitter * 0.2),
      y: cy + Math.sin(angle) * (radius + jitter * 0.2),
    };
  });

  if (nodes.length === 1) {
    positions[nodes[0].id] = { x: cx, y: cy };
    return { positions, width, height };
  }

  const ids = nodes.map((n) => n.id);
  const index = new Map(ids.map((id, i) => [id, i]));
  const links = edges
    .map((e) => ({ s: index.get(e.source), t: index.get(e.target) }))
    .filter((l): l is { s: number; t: number } => l.s != null && l.t != null && l.s !== l.t);

  for (let iter = 0; iter < iterations; iter++) {
    const cooling = 1 - iter / iterations;
    // repulsion
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = positions[ids[i]];
        const b = positions[ids[j]];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.hypot(dx, dy) || 0.01;
        const force = ((120 * 120) / dist) * cooling * 0.02;
        dx = (dx / dist) * force;
        dy = (dy / dist) * force;
        a.x += dx;
        a.y += dy;
        b.x -= dx;
        b.y -= dy;
      }
    }
    // attraction along edges
    for (const { s, t } of links) {
      const a = positions[ids[s]];
      const b = positions[ids[t]];
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      const dist = Math.hypot(dx, dy) || 0.01;
      const force = (dist - 100) * 0.02 * cooling;
      dx = (dx / dist) * force;
      dy = (dy / dist) * force;
      a.x += dx;
      a.y += dy;
      b.x -= dx;
      b.y -= dy;
    }
    // mild center gravity
    for (const id of ids) {
      const p = positions[id];
      p.x += (cx - p.x) * 0.01;
      p.y += (cy - p.y) * 0.01;
    }
  }

  // Fit into padding box
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const id of ids) {
    const p = positions[id];
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x);
    maxY = Math.max(maxY, p.y);
  }
  const pad = 48;
  const spanX = Math.max(maxX - minX, 1);
  const spanY = Math.max(maxY - minY, 1);
  const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
  for (const id of ids) {
    const p = positions[id];
    p.x = pad + (p.x - minX) * scale;
    p.y = pad + (p.y - minY) * scale;
  }

  return { positions, width, height };
}
