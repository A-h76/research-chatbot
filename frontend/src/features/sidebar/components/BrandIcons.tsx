/** Brand marks for Library import nav — Zotero favicon + Mendeley SVG. */

import { cn } from "@/lib/utils";

export function ZoteroIcon({ className }: { className?: string }) {
  return (
    <img
      src="/brand/zotero.ico"
      alt=""
      width={16}
      height={16}
      className={cn("size-4 shrink-0 object-contain", className)}
      draggable={false}
    />
  );
}

export function MendeleyIcon({ className }: { className?: string }) {
  return (
    <img
      src="/brand/mendeley.svg"
      alt=""
      width={16}
      height={16}
      className={cn("size-4 shrink-0 object-contain", className)}
      draggable={false}
    />
  );
}
