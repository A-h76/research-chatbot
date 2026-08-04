import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ResearchEcosystemCloud } from "@/features/research-flow/ResearchEcosystemCloud";
import "./ecosystem.css";

const el = document.getElementById("dhund-ecosystem-cloud");
if (el) {
  el.replaceChildren();
  createRoot(el).render(
    <StrictMode>
      <div className="dhund-ecosystem-island text-foreground">
        <ResearchEcosystemCloud />
      </div>
    </StrictMode>,
  );
}
