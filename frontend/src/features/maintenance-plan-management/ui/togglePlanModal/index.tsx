"use client";

import ConfirmModal from "@shared/ui/confirmModal";
import { maintenanceScheduleKeys } from "@entities/maintenance-schedule";
import { updateMaintenancePlan } from "@entities/maintenance-plan";
import { maintenancePlanKeys } from "@entities/maintenance-plan";
import { IMaintenancePlan } from "@entities/maintenance-plan";
import { useQueryClient } from "@tanstack/react-query";
import { ButtonAppearance } from "@shared/ui/button";
import { useMutation } from "@tanstack/react-query";
import { FlagAppearance } from "@shared/ui/flag";
import { getErrorMessage } from "@shared/api";
import { ApiErrorCode } from "@shared/api";
import { hasErrorCode } from "@shared/api";
import { useFlags } from "@shared/ui/flag";
import { ReactElement } from "react";

interface ITogglePlanModalProps {
  plan: IMaintenancePlan;
  onClose: () => void;
}

const TogglePlanModal = ({
  plan,
  onClose,
}: ITogglePlanModalProps): ReactElement => {
  const queryClient = useQueryClient();
  const { showFlag } = useFlags();
  const isPausing: boolean = plan.enabled;

  const toggleMutation = useMutation({
    mutationFn: () => updateMaintenancePlan(plan, { enabled: !plan.enabled }),
    onSuccess: (savedPlan) => {
      queryClient.setQueryData(
        maintenancePlanKeys.detail(savedPlan.id),
        savedPlan
      );
      queryClient.invalidateQueries({ queryKey: maintenancePlanKeys.lists() });
      queryClient.invalidateQueries({ queryKey: maintenanceScheduleKeys.all });
      showFlag({
        appearance: FlagAppearance.SUCCESS,
        title: isPausing ? "Регламент приостановлен" : "Регламент возобновлён",
      });
      onClose();
    },
    onError: (error) => {
      if (hasErrorCode(error, ApiErrorCode.VERSION_CONFLICT)) {
        queryClient.invalidateQueries({
          queryKey: maintenancePlanKeys.detail(plan.id),
        });
      }
    },
  });

  const handleConfirm = () => {
    toggleMutation.mutate();
  };

  return (
    <ConfirmModal
      title={isPausing ? "Приостановить регламент?" : "Возобновить регламент?"}
      confirmLabel={isPausing ? "Приостановить" : "Возобновить"}
      confirmAppearance={
        isPausing ? ButtonAppearance.WARNING : ButtonAppearance.PRIMARY
      }
      onConfirm={handleConfirm}
      onClose={onClose}
      isPending={toggleMutation.isPending}
      errorMessage={
        toggleMutation.isError ? getErrorMessage(toggleMutation.error) : null
      }
    >
      {isPausing ? (
        <p>
          Новые плановые заявки и напоминания по регламенту создаваться не
          будут. Уже начатые заявки можно завершить. Графики и их даты
          сохранятся.
        </p>
      ) : (
        <p>
          Графики ТО возобновятся с прежними датами, даже если сроки уже прошли.
          Для нового подходящего оборудования будут созданы графики.
        </p>
      )}
    </ConfirmModal>
  );
};

export default TogglePlanModal;
