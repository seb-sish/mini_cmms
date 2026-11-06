"use client";

import { maintenanceScheduleKeys } from "@entities/maintenance-schedule";
import { notificationKeys } from "@entities/notification";
import { workHistoryKeys } from "@entities/work-history";
import { useQueryClient } from "@tanstack/react-query";
import { workOrderKeys } from "@entities/work-order";
import { useMutation } from "@tanstack/react-query";
import { FlagAppearance } from "@shared/ui/flag";
import { getErrorMessage } from "@shared/api";
import { faultKeys } from "@entities/fault";
import { ApiErrorCode } from "@shared/api";
import { hasErrorCode } from "@shared/api";
import { useFlags } from "@shared/ui/flag";

interface IUseWorkOrderMutationParams<TVariables, TResult> {
  workOrderId: string;
  mutationFn: (variables: TVariables) => Promise<TResult>;
  successTitle?: string;
  onSuccess?: (result: TResult) => void;
  shouldFlagErrors?: boolean;
}

const REFRESH_ON_ERROR_CODES: ApiErrorCode[] = [
  ApiErrorCode.VERSION_CONFLICT,
  ApiErrorCode.INVALID_WORK_ORDER_STATE,
  ApiErrorCode.NOT_FOUND,
];

export const useWorkOrderMutation = <TVariables, TResult>({
  workOrderId,
  mutationFn,
  successTitle,
  onSuccess,
  shouldFlagErrors = false,
}: IUseWorkOrderMutationParams<TVariables, TResult>) => {
  const queryClient = useQueryClient();
  const { showFlag } = useFlags();

  const refreshRelatedData = () => {
    queryClient.invalidateQueries({ queryKey: workOrderKeys.all });
    queryClient.invalidateQueries({ queryKey: faultKeys.all });
    queryClient.invalidateQueries({ queryKey: maintenanceScheduleKeys.all });
    queryClient.invalidateQueries({ queryKey: workHistoryKeys.all });
    queryClient.invalidateQueries({ queryKey: notificationKeys.all });
  };

  return useMutation({
    mutationFn,
    onSuccess: (result) => {
      refreshRelatedData();
      if (successTitle)
        showFlag({ appearance: FlagAppearance.SUCCESS, title: successTitle });
      onSuccess?.(result);
    },
    onError: (error) => {
      if (REFRESH_ON_ERROR_CODES.some((code) => hasErrorCode(error, code))) {
        queryClient.invalidateQueries({
          queryKey: workOrderKeys.detail(workOrderId),
        });
      }

      if (shouldFlagErrors) {
        showFlag({
          appearance: FlagAppearance.ERROR,
          title: "Действие не выполнено",
          description: getErrorMessage(error),
        });
      }
    },
  });
};
