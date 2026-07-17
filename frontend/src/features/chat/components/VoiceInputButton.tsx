import { Mic, MicOff } from "lucide-react";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { cn } from "@/lib/utils";

export function VoiceInputButton({ onTranscript }: { onTranscript: (text: string) => void }) {
  const { listening, toggle, supported } = useSpeechRecognition(onTranscript);
  if (!supported) return null;
  return (
    <button
      type="button"
      onClick={toggle}
      title={listening ? "Stop dictation" : "Dictate"}
      className={cn(
        "inline-flex size-8 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-hover hover:text-foreground",
        listening && "bg-destructive/15 text-destructive"
      )}
    >
      {listening ? <MicOff className="size-4" /> : <Mic className="size-4" />}
    </button>
  );
}
