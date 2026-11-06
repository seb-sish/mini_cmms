"use client";

import Button from "@shared/ui/button";
import EditWorkOrderModal from "../editWorkOrderModal";
import CloseWorkOrderModal from "../closeWorkOrderModal";
import AssignWorkOrderModal from "../assignWorkOrderModal";
import CancelWorkOrderModal from "../cancelWorkOrderModal";
import CompleteWorkOrderModal from "../completeWorkOrderModal";
import { useWorkOrderMutation } from "../../model/useWorkOrderMutation";
import { getWorkOrderActions } from "../../model/workOrderActions";
import { startWorkOrder } from "@entities/work-order";
import { ButtonAppearance } from "@shared/ui/button";
import { IWorkOrder } from "@entities/work-order";
import { IconName } from "@shared/ui/icon";
import { useViewer } from "@entities/user";
import { ReactElement } from "react";
import { useState } from "react";
import "./style.css";

const enum WorkOrderDialog {
  EDIT = "edit",
  ASSIGN = "assign",
  COMPLETE = "complete",
  CLOSE = "close",
  CANCEL = "cancel",
}

interface IWorkOrderActionsBarProps {
  workOrder: IWorkOrder;
}

const WorkOrderActionsBar = ({
  workOrder,
}: IWorkOrderActionsBarProps): ReactElement => {
  const viewer = useViewer();
  const [openedDialog, setOpenedDialog] = useState<WorkOrderDialog | null>(
    null
  );
  const actions = getWorkOrderActions(viewer, workOrder);

  const startMutation = useWorkOrderMutation({
    workOrderId: workOrder.id,
    mutationFn: () => startWorkOrder(workOrder.id),
    successTitle: "Заявка взята в работу",
    shouldFlagErrors: true,
  });

  const closeDialog = () => {
    setOpenedDialog(null);
  };

  const openEdit = () => setOpenedDialog(WorkOrderDialog.EDIT);
  const openAssign = () => setOpenedDialog(WorkOrderDialog.ASSIGN);
  const openComplete = () => setOpenedDialog(WorkOrderDialog.COMPLETE);
  const openClose = () => setOpenedDialog(WorkOrderDialog.CLOSE);
  const openCancel = () => setOpenedDialog(WorkOrderDialog.CANCEL);

  const handleStart = () => {
    startMutation.mutate(undefined);
  };

  return (
    <div className="work-order-actions-bar">
      {actions.canAssign && (
        <Button
          label="Назначить исполнителя"
          appearance={ButtonAppearance.PRIMARY}
          iconBefore={IconName.USER}
          onClick={openAssign}
        />
      )}
      {actions.canStart && (
        <Button
          label="Начать работу"
          appearance={ButtonAppearance.PRIMARY}
          iconBefore={IconName.WRENCH}
          isLoading={startMutation.isPending}
          onClick={handleStart}
        />
      )}
      {actions.canComplete && (
        <Button
          label="Отметить выполнение"
          appearance={ButtonAppearance.PRIMARY}
          iconBefore={IconName.CHECK}
          onClick={openComplete}
        />
      )}
      {actions.canClose && (
        <Button
          label="Принять и закрыть"
          appearance={ButtonAppearance.PRIMARY}
          iconBefore={IconName.CHECK}
          onClick={openClose}
        />
      )}
      {actions.canReassign && (
        <Button
          label="Переназначить"
          iconBefore={IconName.USER}
          onClick={openAssign}
        />
      )}
      {actions.canEdit && (
        <Button
          label="Изменить"
          iconBefore={IconName.EDIT}
          onClick={openEdit}
        />
      )}
      {actions.canCancel && (
        <Button
          label="Отменить заявку"
          appearance={ButtonAppearance.SUBTLE}
          iconBefore={IconName.CLOSE}
          onClick={openCancel}
        />
      )}
      {openedDialog === WorkOrderDialog.EDIT && (
        <EditWorkOrderModal workOrder={workOrder} onClose={closeDialog} />
      )}
      {openedDialog === WorkOrderDialog.ASSIGN && (
        <AssignWorkOrderModal workOrder={workOrder} onClose={closeDialog} />
      )}
      {openedDialog === WorkOrderDialog.COMPLETE && (
        <CompleteWorkOrderModal workOrder={workOrder} onClose={closeDialog} />
      )}
      {openedDialog === WorkOrderDialog.CLOSE && (
        <CloseWorkOrderModal workOrder={workOrder} onClose={closeDialog} />
      )}
      {openedDialog === WorkOrderDialog.CANCEL && (
        <CancelWorkOrderModal workOrder={workOrder} onClose={closeDialog} />
      )}
    </div>
  );
};

export default WorkOrderActionsBar;
