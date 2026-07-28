import { useQuery } from "@tanstack/react-query";
import { collectionsApi } from "../collectionsApi";

export function useLibraryCollections() {
  return useQuery({
    queryKey: ["library", "collections"],
    queryFn: async () => (await collectionsApi.list()).items,
  });
}
