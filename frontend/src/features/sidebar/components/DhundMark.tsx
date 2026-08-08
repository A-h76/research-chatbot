/**
 * Quiet Dhund wordmark glyph — currentColor, no teal tile.
 * Brand color lives in CTAs / research states, not chrome.
 */
export function DhundMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <path
        d="M7 4.5h5.2c3.85 0 6.55 2.45 6.55 7.5S16.05 19.5 12.2 19.5H7V4.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M11.2 8.1H9.15v7.8H11.2c2.15 0 3.45-1.35 3.45-3.9 0-2.55-1.3-3.9-3.45-3.9Z"
        fill="currentColor"
        fillOpacity="0.22"
      />
    </svg>
  );
}
