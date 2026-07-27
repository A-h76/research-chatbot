import { useQuery } from "@tanstack/react-query";
import { filesApi } from "./api";

export function useLibraryFacets(projectId?: number | null) {
  return useQuery({
    queryKey: ["library", "facets", projectId ?? null],
    queryFn: () => filesApi.facets(projectId),
  });
}
