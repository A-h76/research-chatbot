import { useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { modelsApi } from "./api";

export function useModels() {
  return useQuery({
    queryKey: queryKeys.models,
    queryFn: () => modelsApi.list(),
    staleTime: 5 * 60_000,
  });
}

export function useRefreshModels() {
  const qc = useQueryClient();
  return async () => {
    const data = await modelsApi.list(true);
    qc.setQueryData(queryKeys.models, data);
    return data;
  };
}
