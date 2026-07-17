import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "./api";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.get,
    staleTime: 60_000,   // 1 min — dashboard data doesn't need to be live
    refetchOnWindowFocus: true,
  });
}
