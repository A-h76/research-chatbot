import { useEffect, useState } from "react";
import { evidenceApi } from "../api";
import type { ConsensusConflictStripProps } from "../components/ConsensusConflictStrip";

type Status = ConsensusConflictStripProps["status"];

/** Project-scoped consensus+conflict for Compare (RI-003/004). */
export function useProjectConsensusConflict(opts: {
  projectId: number | null;
  fileIds?: number[];
  enabled?: boolean;
}) {
  const { projectId, fileIds = [], enabled = true } = opts;
  const [status, setStatus] = useState<Status>("idle");
  const [consensus, setConsensus] = useState<ConsensusConflictStripProps["consensus"]>(null);
  const [conflict, setConflict] = useState<ConsensusConflictStripProps["conflict"]>(null);

  useEffect(() => {
    if (!enabled || projectId == null) {
      setStatus("idle");
      setConsensus(null);
      setConflict(null);
      return;
    }
    let cancelled = false;
    setStatus("loading");
    const query = {
      intent: "compare_topic",
      scope: {
        project_id: projectId,
        file_ids: fileIds.length ? fileIds : null,
      },
      filters: {
        status: ["accepted", "candidate"],
        require_page_anchor: true,
      },
      ranking_strategy: "default_v0",
      result_limit: 40,
      query_text: "",
    };
    evidenceApi
      .conflict(query)
      .then((raw) => {
        if (cancelled) return;
        const body = raw as {
          consensus?: ConsensusConflictStripProps["consensus"];
          conflict?: ConsensusConflictStripProps["conflict"];
        };
        setConsensus(body.consensus ?? null);
        setConflict(body.conflict ?? null);
        setStatus("ok");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("error");
        setConsensus(null);
        setConflict(null);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, enabled, fileIds.join(",")]);

  return { status, consensus, conflict };
}
