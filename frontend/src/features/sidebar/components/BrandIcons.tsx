/** Compact brand marks for Library import nav (Zotero / Mendeley). */

export function ZoteroIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      aria-hidden
      focusable="false"
    >
      <rect width="24" height="24" rx="5" fill="#CC2936" />
      <text
        x="12"
        y="16.5"
        textAnchor="middle"
        fill="#fff"
        fontSize="13"
        fontWeight="700"
        fontFamily="system-ui, -apple-system, sans-serif"
      >
        Z
      </text>
    </svg>
  );
}

export function MendeleyIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      aria-hidden
      focusable="false"
    >
      <rect width="24" height="24" rx="5" fill="#A51C30" />
      <text
        x="12"
        y="16.5"
        textAnchor="middle"
        fill="#fff"
        fontSize="12"
        fontWeight="700"
        fontFamily="system-ui, -apple-system, sans-serif"
      >
        M
      </text>
    </svg>
  );
}
