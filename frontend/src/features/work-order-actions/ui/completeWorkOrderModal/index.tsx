"use client";

import Tag from "@shared/ui/tag";
import Button from "@shared/ui/button";
import TextArea from "@shared/ui/textArea";
import TextField from "@shared/ui/textField";
import FormModal from "@shared/ui/formModal";
import SectionMessage from "@shared/ui/sectionMessage";
import { useMaintenanceScheduleQuery } from "@entities/maintenance-schedule";
import { useWorkOrderMutation } from "../../model/useWorkOrderMutation";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { useMaintenancePlanQuery } from "@entities/maintenance-plan";
import { INITIAL_COMPLETE_VALUES } from "../../model/workOrderForms";
import { validateReplacedPart } from "../../model/workOrderForms";
import { validateCompleteForm } from "../../model/workOrderForms";
import { getEarliestCompletionDate } from "@entities/work-order";
import { getMissingRequiredItems } from "@entities/work-order";
import { toCompletePayload } from "../../model/workOrderForms";
import { isTooEarlyToComplete } from "@entities/work-order";
import { WORK_ORDER_LIMITS } from "@entities/work-order";
import { completeWorkOrder } from "@entities/work-order";
import { WorkOrderType } from "@entities/work-order";
import { getCompanyToday } from "@shared/lib/date";
import { IWorkOrder } from "@entities/work-order";
import { normalizeText } from "@shared/lib/form";
import { useFormFields } from "@shared/lib/form";
import { getErrorMessage } from "@shared/api";
import { formatDate } from "@shared/lib/date";
import { hasErrors } from "@shared/lib/form";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import "./style.css";

interface ICompleteWorkOrderModalProps {
  workOrder: IWorkOrder;
  onClose: () => void;
}

const CompleteWorkOrderModal = ({
  workOrder,
  onClose,
}: ICompleteWorkOrderModalProps): ReactElement => {
  const { values, errors, setErrors, setFieldValue } = useFormFields(
    INITIAL_COMPLETE_VALUES
  );
  const isPlanned: boolean = workOrder.type === WorkOrderType.PLANNED;
  const missingItems = getMissingRequiredItems(workOrder.checklist);
  const { data: schedule } = useMaintenanceScheduleQuery(
    workOrder.schedule_id ?? "",
    isPlanned && Boolean(workOrder.schedule_id)
  );
  const { data: plan } = useMaintenancePlanQuery(
    schedule?.plan_id ?? "",
    Boolean(schedule)
  );

  const earliestDate: string | null =
    plan && workOrder.planned_due_on
      ? getEarliestCompletionDate(workOrder.planned_due_on, plan.interval_days)
      : null;
  const isTooEarly: boolean = Boolean(
    plan &&
      workOrder.planned_due_on &&
      isTooEarlyToComplete(
        getCompanyToday(),
        workOrder.planned_due_on,
        plan.interval_days
      )
  );

  const completeMutation = useWorkOrderMutation({
    workOrderId: workOrder.id,
    mutationFn: () =>
      completeWorkOrder(workOrder.id, toCompletePayload(values)),
    successTitle: "Работа отмечена как выполненная",
    onSuccess: onClose,
  });

  const updateResult = (value: string) => {
    setFieldValue("result", value);
  };

  const updatePartDraft = (value: string) => {
    setFieldValue("partDraft", value);
  };

  const handleAddPart = () => {
    const partError = validateReplacedPart(
      values.partDraft,
      values.replacedParts
    );

    if (partError) {
      setErrors((prev) => ({ ...prev, partDraft: partError }));
      return;
    }

    setFieldValue("replacedParts", [
      ...values.replacedParts,
      normalizeText(values.partDraft),
    ]);
    setFieldValue("partDraft", "");
  };

  const handleSubmit = () => {
    const validationErrors = validateCompleteForm(values);

    setErrors(validationErrors);

    if (hasErrors(validationErrors) || missingItems.length > 0) return;

    completeMutation.mutate(undefined);
  };

  return (
    <FormModal
      title={`Выполнение заявки ${workOrder.number}`}
      submitLabel="Отметить выполнение"
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={completeMutation.isPending}
      isSubmitDisabled={missingItems.length > 0 || isTooEarly}
      errorMessage={
        completeMutation.isError
          ? getErrorMessage(completeMutation.error)
          : null
      }
    >
      {missingItems.length > 0 && (
        <SectionMessage
          appearance={SectionMessageAppearance.WARNING}
          title="Чек-лист не завершён"
        >
          <p>Перед завершением отметьте обязательные пункты:</p>
          <ul className="complete-work-order-missing">
            {missingItems.map((item) => (
              <li key={item.id}>{item.title}</li>
            ))}
          </ul>
        </SectionMessage>
      )}
      {isTooEarly && earliestDate && (
        <SectionMessage
          appearance={SectionMessageAppearance.WARNING}
          title="Слишком рано для планового ТО"
        >
          <p>
            Выполнение по сроку {formatDate(workOrder.planned_due_on ?? "")}{" "}
            допустимо не раньше {formatDate(earliestDate)}, иначе следующий срок
            не сдвинется вперёд.
          </p>
        </SectionMessage>
      )}
      <TextArea
        label="Результат работ"
        value={values.result}
        onChange={updateResult}
        errorMessage={errors.result}
        helperText="Что сделано, в каком состоянии оставлено оборудование"
        maxLength={WORK_ORDER_LIMITS.RESULT_MAX}
        rows={5}
        isRequired
      />
      <div className="complete-work-order-parts">
        <div className="complete-work-order-part-input">
          <TextField
            label="Заменённая деталь"
            value={values.partDraft}
            onChange={updatePartDraft}
            errorMessage={errors.partDraft}
            maxLength={WORK_ORDER_LIMITS.REPLACED_PART_MAX}
            placeholder="Например: подшипник 6204"
          />
          <Button
            label="Добавить"
            iconBefore={IconName.ADD}
            onClick={handleAddPart}
          />
        </div>
        {values.replacedParts.length > 0 && (
          <ul
            className="complete-work-order-tags"
            aria-label="Заменённые детали"
          >
            {values.replacedParts.map((part, index) => {
              const handleRemove = () => {
                setFieldValue(
                  "replacedParts",
                  values.replacedParts.filter(
                    (_, partIndex) => partIndex !== index
                  )
                );
              };

              return (
                <li key={`${part}-${index}`}>
                  <Tag label={part} onRemove={handleRemove} />
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <p className="body-small text-subtle">
        Дата и время выполнения фиксируются сервером в момент отметки.
      </p>
    </FormModal>
  );
};

export default CompleteWorkOrderModal;
