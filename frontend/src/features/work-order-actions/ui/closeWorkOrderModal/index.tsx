"use client";

import ConfirmModal from "@shared/ui/confirmModal";
import { useWorkOrderMutation } from "../../model/useWorkOrderMutation";
import { closeWorkOrder } from "@entities/work-order";
import { WorkOrderType } from "@entities/work-order";
import { IWorkOrder } from "@entities/work-order";
import { getErrorMessage } from "@shared/api";
import { ReactElement } from "react";

interface ICloseWorkOrderModalProps {
  workOrder: IWorkOrder;
  onClose: () => void;
}

const CloseWorkOrderModal = ({
  workOrder,
  onClose,
}: ICloseWorkOrderModalProps): ReactElement => {
  const closeMutation = useWorkOrderMutation({
    workOrderId: workOrder.id,
    mutationFn: () => closeWorkOrder(workOrder.id),
    successTitle: "Работа принята, заявка закрыта",
    onSuccess: onClose,
  });

  const handleConfirm = () => {
    closeMutation.mutate(undefined);
  };

  return (
    <ConfirmModal
      title="Принять работу и закрыть заявку?"
      confirmLabel="Закрыть заявку"
      onConfirm={handleConfirm}
      onClose={onClose}
      isPending={closeMutation.isPending}
      errorMessage={
        closeMutation.isError ? getErrorMessage(closeMutation.error) : null
      }
    >
      <p>
        В историю работ будет записан результат, исполнитель и заменённые
        детали. Закрытую заявку и запись истории изменить нельзя.
      </p>
      {workOrder.type === WorkOrderType.PLANNED ? (
        <p className="text-subtle">
          Дата последнего ТО станет датой фактического выполнения, следующий
          срок будет рассчитан по периодичности регламента.
        </p>
      ) : (
        workOrder.fault_id && (
          <p className="text-subtle">
            Связанная неисправность получит статус &quot;Устранена&quot;.
          </p>
        )
      )}
    </ConfirmModal>
  );
};

export default CloseWorkOrderModal;
