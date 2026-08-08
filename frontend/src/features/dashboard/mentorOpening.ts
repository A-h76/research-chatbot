/**
 * Conversational Research Mentor opening — supervisor beside you, not a status panel.
 * Uses the same project / nextAction reality as Home.
 */

export function greetingHour(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function paperWords(n: number): string {
  if (n <= 0) return "your papers";
  if (n === 1) return "your one imported paper";
  const words = [
    "",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
  ];
  const count = n <= 12 ? words[n] : String(n);
  return `your ${count} imported papers`;
}

function recommendationPhrase(actionId: string, papers: number): string {
  switch (actionId) {
    case "extract_evidence":
      return `extracting evidence from ${paperWords(papers)}`;
    case "import_papers":
      return "importing papers into your library";
    case "review_gaps":
      return "reviewing the research gaps in your corpus";
    case "inspect_contradictions":
      return "looking closely at contradictions across your papers";
    case "start_writing":
      return "starting a draft from your evidence";
    case "unread_papers":
      return "catching up on unread papers";
    case "compare_papers":
      return "comparing papers side by side";
    default:
      return "continuing your research";
  }
}

export function buildMentorOpening(opts: {
  firstName: string;
  projectTitle: string | null;
  papers: number;
  nextActionId: string | null;
}): string[] {
  const name = opts.firstName ? `, ${opts.firstName}` : "";
  const lines: string[] = [`${greetingHour()}${name}.`];

  if (opts.projectTitle) {
    lines.push(`You're currently building your ${opts.projectTitle}.`);
  } else {
    lines.push("You're just getting started — we can shape the research together.");
  }

  const actionId = opts.nextActionId || "import_papers";
  lines.push(
    `Today's recommendation is ${recommendationPhrase(actionId, opts.papers)}.`,
  );
  lines.push(
    "Need help planning your review, finding literature, or understanding a paper?",
  );
  return lines;
}
