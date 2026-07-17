export interface SSEEvent {
  event: string;
  data: any;
}

// Direct port of the buffer/split-on-"\n\n" + `event:`/`data:` regex parsing
// used by the previous vanilla-JS client — keeps the wire format unchanged.
export async function* iterateSSE(
  body: ReadableStream<Uint8Array>
): AsyncGenerator<SSEEvent> {
  const reader = body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const evM = part.match(/^event: (.+)$/m);
      const dataM = part.match(/^data: (.+)$/m);
      if (!evM || !dataM) continue;
      yield { event: evM[1], data: JSON.parse(dataM[1]) };
    }
  }
}
