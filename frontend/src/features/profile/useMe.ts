import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { profileApi } from "./api";
import type { Me } from "@/types/api";

export function useMe() {
  return useQuery({ queryKey: queryKeys.me, queryFn: profileApi.me });
}

export function useUpdateInstructions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (custom_instructions: string) => profileApi.updateInstructions(custom_instructions),
    onSuccess: (_data, custom_instructions) => {
      qc.setQueryData<Me>(queryKeys.me, (old) =>
        old ? { ...old, custom_instructions } : old
      );
    },
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name?: string; custom_instructions?: string }) =>
      profileApi.updateProfile(data),
    onSuccess: (_data, vars) => {
      qc.setQueryData<Me>(queryKeys.me, (old) =>
        old
          ? {
              ...old,
              ...(vars.name !== undefined ? { name: vars.name } : {}),
              ...(vars.custom_instructions !== undefined
                ? { custom_instructions: vars.custom_instructions }
                : {}),
            }
          : old
      );
    },
  });
}
