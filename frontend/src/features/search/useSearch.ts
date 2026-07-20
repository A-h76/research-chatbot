import { useMutation } from "@tanstack/react-query";
import { searchApi, ragApi, type SearchInput, type RagInput } from "./api";

export function useSearch() {
  return useMutation({
    mutationFn: (body: SearchInput) => searchApi.search(body),
  });
}

export function useAskAi() {
  return useMutation({
    mutationFn: (body: RagInput) => ragApi.ask(body),
  });
}
