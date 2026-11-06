"use client";

import Select from "@shared/ui/select";
import TextArea from "@shared/ui/textArea";
import TextField from "@shared/ui/textField";
import FormModal from "@shared/ui/formModal";
import { buildWorkOrderPatchPayload } from "../../model/workOrderForms";
import { useWorkOrderMutation } from "../../model/useWorkOrderMutation";
import { validateWorkOrderEditForm } from "../../model/workOrderForms";
import { toWorkOrderEditValues } from "../../model/workOrderForms";
import { WORK_ORDER_PRIORITY_LABELS } from "@entities/work-order";
import { WORK_ORDER_PRIORITIES } from "@entities/work-order";
import { WORK_ORDER_LIMITS } from "@entities/work-order";
import { WorkOrderPriority } from "@entities/work-order";
import { updateWorkOrder } from "@entities/work-order";
import { buildOptions } from "@shared/lib/options";
import { IWorkOrder } from "@entities/work-order";
import { useFormFields } from "@shared/lib/form";
import { getErrorMessage } from "@shared/api";
import { hasErrors } from "@shared/lib/form";
import { ReactElement } from "react";

interface IEditWorkOrderModalProps {
  workOrder: IWorkOrder;
  onClose: () => void;
}

const PRIORITY_OPTIONS = buildOptions(
  WORK_ORDER_PRIORITIES,
  WORK_ORDER_PRIORITY_LABELS
);

const EditWorkOrderModal = ({
  workOrder,
  onClose,
}: IEditWorkOrderModalProps): ReactElement => {
  const { values, errors, setErrors, setFieldValue } = useFormFields(
    toWorkOrderEditValues(workOrder)
  );
  const patchPayload = buildWorkOrderPatchPayload(workOrder, values);

  const editMutation = useWorkOrderMutation({
    workOrderId: workOrder.id,
    mutationFn: () => updateWorkOrder(workOrder, patchPayload),
    successTitle: "Заявка обновлена",
    onSuccess: onClose,
  });

  const handleSubmit = () => {
    const validationErrors = validateWorkOrderEditForm(values);

    setErrors(validationErrors);

    if (hasErrors(validationErrors)) return;

    editMutation.mutate(undefined);
  };

  const updateTitle = (value: string) => {
    setFieldValue("title", value);
  };

  const updateDescription = (value: string) => {
    setFieldValue("description", value);
  };

  const updatePriority = (value: string) => {
    setFieldValue("priority", value as WorkOrderPriority);
  };

  return (
    <FormModal
      title={`Редактирование ${workOrder.number}`}
      submitLabel="Сохранить"
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={editMutation.isPending}
      isSubmitDisabled={Object.keys(patchPayload).length === 0}
      errorMessage={
        editMutation.isError ? getErrorMessage(editMutation.error) : null
      }
    >
      <TextField
        label="Заголовок"
        value={values.title}
        onChange={updateTitle}
        errorMessage={errors.title}
        maxLength={WORK_ORDER_LIMITS.TITLE_MAX}
        isRequired
      />
      <TextArea
        label="Описание работ"
        value={values.description}
        onChange={updateDescription}
        errorMessage={errors.description}
        maxLength={WORK_ORDER_LIMITS.DESCRIPTION_MAX}
        isRequired
      />
      <Select
        label="Приоритет"
        value={values.priority}
        options={PRIORITY_OPTIONS}
        onChange={updatePriority}
        isRequired
      />
    </FormModal>
  );
};

export default EditWorkOrderModal;
