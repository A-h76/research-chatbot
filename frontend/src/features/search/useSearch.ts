import { useMutation } from "@tanstack/react-query";
import { searchApi, type SearchInput } from "./api";

export function useSearch() {
  return useMutation({
    mutationFn: (body: SearchInput) => searchApi.search(body),
  });
}
