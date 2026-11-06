"use client";

import Select from "@shared/ui/select";
import TextField from "@shared/ui/textField";
import FormModal from "@shared/ui/formModal";
import SectionMessage from "@shared/ui/sectionMessage";
import { useWorkOrderMutation } from "../../model/useWorkOrderMutation";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { validateAssigneeId } from "../../model/workOrderForms";
import { reassignWorkOrder } from "@entities/work-order";
import { assignWorkOrder } from "@entities/work-order";
import { useTechniciansQuery } from "@entities/user";
import { ISelectOption } from "@shared/lib/options";
import { IWorkOrder } from "@entities/work-order";
import { getErrorMessage } from "@shared/api";
import { ReactElement } from "react";
import { useState } from "react";

interface IAssignWorkOrderModalProps {
  workOrder: IWorkOrder;
  onClose: () => void;
}

const AssignWorkOrderModal = ({
  workOrder,
  onClose,
}: IAssignWorkOrderModalProps): ReactElement => {
  const isReassign: boolean = workOrder.assignee_id !== null;
  const [assigneeId, setAssigneeId] = useState<string>("");
  const [assigneeError, setAssigneeError] = useState<string | undefined>();
  const {
    data: technicians,
    isError: isDirectoryUnavailable,
    isLoading,
  } = useTechniciansQuery(true);

  const technicianOptions: ISelectOption[] = (technicians?.items ?? [])
    .filter((technician) => technician.id !== workOrder.assignee_id)
    .map((technician) => ({ value: technician.id, label: technician.login }));

  const assignMutation = useWorkOrderMutation({
    workOrderId: workOrder.id,
    mutationFn: (technicianId: string) =>
      isReassign
        ? reassignWorkOrder(workOrder.id, technicianId)
        : assignWorkOrder(workOrder.id, technicianId),
    successTitle: isReassign ? "Исполнитель изменён" : "Исполнитель назначен",
    onSuccess: onClose,
  });

  const updateAssignee = (value: string) => {
    setAssigneeId(value);
    setAssigneeError(undefined);
  };

  const handleSubmit = () => {
    const validationError = validateAssigneeId(assigneeId);

    setAssigneeError(validationError);

    if (validationError) return;

    assignMutation.mutate(assigneeId.trim());
  };

  return (
    <FormModal
      title={isReassign ? "Переназначить исполнителя" : "Назначить исполнителя"}
      submitLabel={isReassign ? "Переназначить" : "Назначить"}
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={assignMutation.isPending}
      errorMessage={
        assignMutation.isError ? getErrorMessage(assignMutation.error) : null
      }
    >
      {isReassign && (
        <p className="text-subtle">
          Прежний исполнитель потеряет доступ к заявке. Статус заявки
          сохранится.
        </p>
      )}
      {isDirectoryUnavailable ? (
        <>
          <SectionMessage
            appearance={SectionMessageAppearance.WARNING}
            title="Справочник техников недоступен"
          >
            <p>
              Сервер не предоставляет главному инженеру список сотрудников.
              Укажите идентификатор техника, полученный у администратора.
            </p>
          </SectionMessage>
          <TextField
            label="Идентификатор техника (UUID)"
            value={assigneeId}
            onChange={updateAssignee}
            errorMessage={assigneeError}
            placeholder="00000000-0000-0000-0000-000000000000"
            isRequired
          />
        </>
      ) : (
        <Select
          label="Техник"
          value={assigneeId}
          options={technicianOptions}
          onChange={updateAssignee}
          placeholder={isLoading ? "Загрузка..." : "Выберите техника"}
          errorMessage={assigneeError}
          helperText="Показаны только активные пользователи с ролью техника"
          isRequired
        />
      )}
    </FormModal>
  );
};

export default AssignWorkOrderModal;
