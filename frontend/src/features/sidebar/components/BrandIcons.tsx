/** Brand marks for Library import nav — bundled via Vite (works in SPA catch-all). */

import { cn } from "@/lib/utils";
import zoteroIconUrl from "@/assets/brand/zotero.ico";
import mendeleyIconUrl from "@/assets/brand/mendeley.svg";

export function ZoteroIcon({ className }: { className?: string }) {
  return (
    <img
      src={zoteroIconUrl}
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
      src={mendeleyIconUrl}
      alt=""
      width={16}
      height={16}
      className={cn("size-4 shrink-0 object-contain", className)}
      draggable={false}
    />
  );
}
