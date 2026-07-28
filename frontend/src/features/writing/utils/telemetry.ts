type WritingTelemetryPayload = Record<string, string | number | boolean | null | undefined>;

/** Slice 0 telemetry wrapper. No document content is ever emitted. */
export function trackWritingEvent(eventName: string, payload: WritingTelemetryPayload = {}) {
  window.dispatchEvent(
    new CustomEvent("writing:telemetry", {
      detail: {
        event: eventName,
        payload,
      },
    }),
  );
}

