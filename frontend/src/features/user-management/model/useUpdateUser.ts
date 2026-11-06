"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { IUserPatchPayload } from "@entities/user";
import { FlagAppearance } from "@shared/ui/flag";
import { updateUser } from "@entities/user";
import { ApiErrorCode } from "@shared/api";
import { hasErrorCode } from "@shared/api";
import { useFlags } from "@shared/ui/flag";
import { userKeys } from "@entities/user";
import { IUser } from "@entities/user";

interface IUseUpdateUserParams {
  user: IUser;
  successTitle: string;
  onSuccess?: () => void;
}

export const useUpdateUser = ({
  user,
  successTitle,
  onSuccess,
}: IUseUpdateUserParams) => {
  const queryClient = useQueryClient();
  const { showFlag } = useFlags();

  return useMutation({
    mutationFn: (payload: IUserPatchPayload) => updateUser(user, payload),
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(userKeys.detail(updatedUser.id), updatedUser);
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
      showFlag({ appearance: FlagAppearance.SUCCESS, title: successTitle });
      onSuccess?.();
    },
    onError: (error) => {
      if (hasErrorCode(error, ApiErrorCode.VERSION_CONFLICT)) {
        queryClient.invalidateQueries({ queryKey: userKeys.detail(user.id) });
      }
    },
  });
};
