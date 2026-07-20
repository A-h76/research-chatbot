import { useQuery, useMutation } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { aiApi, type AiTestInput } from "./api";

export function useAiPrompts() {
  return useQuery({
    queryKey: queryKeys.aiPrompts,
    queryFn: () => aiApi.listPrompts(),
  });
}

export function useAiTest() {
  return useMutation({
    mutationFn: (body: AiTestInput) => aiApi.test(body),
  });
}
