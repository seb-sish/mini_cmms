"use client";

import TextArea from "@shared/ui/textArea";
import FormModal from "@shared/ui/formModal";
import { validateCancellationReason } from "../../model/workOrderForms";
import { useWorkOrderMutation } from "../../model/useWorkOrderMutation";
import { WORK_ORDER_LIMITS } from "@entities/work-order";
import { cancelWorkOrder } from "@entities/work-order";
import { ButtonAppearance } from "@shared/ui/button";
import { IWorkOrder } from "@entities/work-order";
import { normalizeText } from "@shared/lib/form";
import { getErrorMessage } from "@shared/api";
import { ReactElement } from "react";
import { useState } from "react";

interface ICancelWorkOrderModalProps {
  workOrder: IWorkOrder;
  onClose: () => void;
}

const CancelWorkOrderModal = ({
  workOrder,
  onClose,
}: ICancelWorkOrderModalProps): ReactElement => {
  const [reason, setReason] = useState<string>("");
  const [reasonError, setReasonError] = useState<string | undefined>();

  const cancelMutation = useWorkOrderMutation({
    workOrderId: workOrder.id,
    mutationFn: (cancellationReason: string) =>
      cancelWorkOrder(workOrder.id, cancellationReason),
    successTitle: "Заявка отменена",
    onSuccess: onClose,
  });

  const updateReason = (value: string) => {
    setReason(value);
    setReasonError(undefined);
  };

  const handleSubmit = () => {
    const validationError = validateCancellationReason(reason);

    setReasonError(validationError);

    if (validationError) return;

    cancelMutation.mutate(normalizeText(reason));
  };

  return (
    <FormModal
      title={`Отменить заявку ${workOrder.number}?`}
      submitLabel="Отменить заявку"
      submitAppearance={ButtonAppearance.DANGER}
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={cancelMutation.isPending}
      errorMessage={
        cancelMutation.isError ? getErrorMessage(cancelMutation.error) : null
      }
    >
      <p className="text-subtle">
        Отменённая заявка не попадает в историю работ. Неисправность останется
        открытой, график ТО не изменится: по ним можно будет создать новую
        заявку.
      </p>
      <TextArea
        label="Причина отмены"
        value={reason}
        onChange={updateReason}
        errorMessage={reasonError}
        maxLength={WORK_ORDER_LIMITS.CANCELLATION_REASON_MAX}
        isRequired
      />
    </FormModal>
  );
};

export default CancelWorkOrderModal;
