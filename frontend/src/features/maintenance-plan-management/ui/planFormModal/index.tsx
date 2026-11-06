"use client";

import Select from "@shared/ui/select";
import TextField from "@shared/ui/textField";
import FormModal from "@shared/ui/formModal";
import ChecklistEditor from "../checklistEditor";
import SectionMessage from "@shared/ui/sectionMessage";
import { maintenanceScheduleKeys } from "@entities/maintenance-schedule";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { useEquipmentDictionariesQuery } from "@entities/equipment";
import { createMaintenancePlan } from "@entities/maintenance-plan";
import { updateMaintenancePlan } from "@entities/maintenance-plan";
import { maintenancePlanKeys } from "@entities/maintenance-plan";
import { PLAN_SCOPE_LABELS } from "@entities/maintenance-plan";
import { buildInitialPlanValues } from "../../model/planForm";
import { IMaintenancePlan } from "@entities/maintenance-plan";
import { buildPlanPatchPayload } from "../../model/planForm";
import { IChecklistDraftItem } from "../../model/planForm";
import { toPlanCreatePayload } from "../../model/planForm";
import { hasPlanFormErrors } from "../../model/planForm";
import { PLAN_SCOPES } from "@entities/maintenance-plan";
import { PLAN_LIMITS } from "@entities/maintenance-plan";
import { validatePlanForm } from "../../model/planForm";
import { toPlanFormValues } from "../../model/planForm";
import { useQueryClient } from "@tanstack/react-query";
import { IPlanFormValues } from "../../model/planForm";
import { IPlanFormErrors } from "../../model/planForm";
import { PlanScope } from "@entities/maintenance-plan";
import { EquipmentPicker } from "@entities/equipment";
import { TextFieldType } from "@shared/ui/textField";
import { useMutation } from "@tanstack/react-query";
import { getCompanyToday } from "@shared/lib/date";
import { buildOptions } from "@shared/lib/options";
import { FlagAppearance } from "@shared/ui/flag";
import { getErrorMessage } from "@shared/api";
import { ModalWidth } from "@shared/ui/modal";
import { getFieldErrors } from "@shared/api";
import { ApiErrorCode } from "@shared/api";
import { hasErrorCode } from "@shared/api";
import { useFlags } from "@shared/ui/flag";
import { ReactElement } from "react";
import { useState } from "react";

interface IPlanFormModalProps {
  plan?: IMaintenancePlan;
  equipmentId?: string;
  onClose: () => void;
  onSaved?: (plan: IMaintenancePlan) => void;
}

const SCOPE_OPTIONS = buildOptions(PLAN_SCOPES, PLAN_SCOPE_LABELS);

const PlanFormModal = ({
  plan,
  equipmentId,
  onClose,
  onSaved,
}: IPlanFormModalProps): ReactElement => {
  const queryClient = useQueryClient();
  const { showFlag } = useFlags();
  const isEditMode: boolean = Boolean(plan);
  const { data: dictionaries } = useEquipmentDictionariesQuery(!isEditMode);
  const [values, setValues] = useState<IPlanFormValues>(() => {
    if (plan) return toPlanFormValues(plan);

    return {
      ...buildInitialPlanValues(getCompanyToday()),
      equipment_id: equipmentId ?? "",
    };
  });
  const [errors, setErrors] = useState<IPlanFormErrors>({});
  const patchPayload = plan ? buildPlanPatchPayload(plan, values) : null;

  const setFieldValue = <TKey extends keyof IPlanFormValues>(
    key: TKey,
    value: IPlanFormValues[TKey]
  ) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: undefined }));
  };

  const saveMutation = useMutation({
    mutationFn: () =>
      plan && patchPayload
        ? updateMaintenancePlan(plan, patchPayload)
        : createMaintenancePlan(toPlanCreatePayload(values)),
    onSuccess: (savedPlan) => {
      queryClient.setQueryData(
        maintenancePlanKeys.detail(savedPlan.id),
        savedPlan
      );
      queryClient.invalidateQueries({ queryKey: maintenancePlanKeys.lists() });
      queryClient.invalidateQueries({ queryKey: maintenanceScheduleKeys.all });
      showFlag({
        appearance: FlagAppearance.SUCCESS,
        title: isEditMode ? "Регламент сохранён" : "Регламент создан",
        description: isEditMode
          ? undefined
          : "Графики ТО для подходящего оборудования сформированы.",
      });
      onSaved?.(savedPlan);
      onClose();
    },
    onError: (error) => {
      setErrors((prev) => ({ ...prev, ...getFieldErrors(error) }));

      if (plan && hasErrorCode(error, ApiErrorCode.VERSION_CONFLICT)) {
        queryClient.invalidateQueries({
          queryKey: maintenancePlanKeys.detail(plan.id),
        });
      }
    },
  });

  const handleSubmit = () => {
    const validationErrors = validatePlanForm(values, isEditMode);

    setErrors(validationErrors);

    if (hasPlanFormErrors(validationErrors)) return;

    saveMutation.mutate();
  };

  const updateName = (value: string) => {
    setFieldValue("name", value);
  };

  const updateScope = (value: string) => {
    setFieldValue("scope", value as PlanScope);
  };

  const updateEquipment = (value: string) => {
    setFieldValue("equipment_id", value);
  };

  const updateCategory = (value: string) => {
    setFieldValue("category", value);
  };

  const updateInterval = (value: string) => {
    setFieldValue("interval_days", value);
  };

  const updateFirstDueOn = (value: string) => {
    setFieldValue("first_due_on", value);
  };

  const updateChecklist = (items: IChecklistDraftItem[]) => {
    setValues((prev) => ({ ...prev, checklist: items }));
    setErrors((prev) => ({
      ...prev,
      checklist: undefined,
      checklistItems: undefined,
    }));
  };

  const isUnchanged: boolean =
    Boolean(patchPayload) && Object.keys(patchPayload ?? {}).length === 0;

  return (
    <FormModal
      title={isEditMode ? "Редактирование регламента ТО" : "Новый регламент ТО"}
      submitLabel={isEditMode ? "Сохранить" : "Создать"}
      onSubmit={handleSubmit}
      onClose={onClose}
      width={ModalWidth.LARGE}
      isSubmitting={saveMutation.isPending}
      isSubmitDisabled={isUnchanged}
      errorMessage={
        saveMutation.isError ? getErrorMessage(saveMutation.error) : null
      }
    >
      <TextField
        label="Название регламента"
        value={values.name}
        onChange={updateName}
        errorMessage={errors.name}
        maxLength={PLAN_LIMITS.NAME_MAX}
        isRequired
      />
      <Select
        label="Область применения"
        value={values.scope}
        options={SCOPE_OPTIONS}
        onChange={updateScope}
        isDisabled={isEditMode}
        helperText={
          isEditMode
            ? "Область регламента после создания не меняется"
            : undefined
        }
        isRequired
      />
      {values.scope === PlanScope.EQUIPMENT ? (
        <EquipmentPicker
          label="Оборудование"
          value={values.equipment_id}
          onChange={updateEquipment}
          errorMessage={errors.equipment_id}
          isDisabled={isEditMode}
          isRequired
        />
      ) : (
        <TextField
          label="Категория оборудования"
          value={values.category}
          onChange={updateCategory}
          errorMessage={errors.category}
          helperText="Регламент применится ко всему неархивному оборудованию этой категории"
          maxLength={PLAN_LIMITS.CATEGORY_MAX}
          suggestions={dictionaries?.categories}
          isDisabled={isEditMode}
          isRequired
        />
      )}
      <div className="form-modal-row">
        <TextField
          label="Периодичность, дней"
          type={TextFieldType.NUMBER}
          value={values.interval_days}
          onChange={updateInterval}
          errorMessage={errors.interval_days}
          helperText={`От ${PLAN_LIMITS.INTERVAL_MIN} до ${PLAN_LIMITS.INTERVAL_MAX}`}
          min={String(PLAN_LIMITS.INTERVAL_MIN)}
          max={String(PLAN_LIMITS.INTERVAL_MAX)}
          isRequired
        />
        <TextField
          label="Дата первого ТО"
          type={TextFieldType.DATE}
          value={values.first_due_on}
          onChange={updateFirstDueOn}
          errorMessage={errors.first_due_on}
          helperText={
            isEditMode
              ? "Задаётся при создании регламента"
              : "Если дата в прошлом, первым сроком станет сегодняшний день"
          }
          isDisabled={isEditMode}
          isRequired
        />
      </div>
      {isEditMode && patchPayload?.interval_days !== undefined && (
        <SectionMessage appearance={SectionMessageAppearance.WARNING}>
          <p>
            После выполненного ТО следующий срок будет пересчитан от даты
            последнего ТО с новой периодичностью. Изменение невозможно при
            незакрытых плановых заявках по регламенту.
          </p>
        </SectionMessage>
      )}
      <ChecklistEditor
        items={values.checklist}
        onChange={updateChecklist}
        errorMessage={errors.checklist}
        itemErrors={errors.checklistItems}
      />
      {isEditMode && (
        <p className="body-small text-subtle">
          Новый чек-лист применяется к будущим заявкам. В уже созданных заявках
          сохраняется прежний список операций.
        </p>
      )}
    </FormModal>
  );
};

export default PlanFormModal;
