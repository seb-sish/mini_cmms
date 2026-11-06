"use client";

import Select from "@shared/ui/select";
import TextArea from "@shared/ui/textArea";
import TextField from "@shared/ui/textField";
import FormModal from "@shared/ui/formModal";
import { buildInitialFaultValues } from "../../model/faultForm";
import { buildFaultPatchPayload } from "../../model/faultForm";
import { toFaultCreatePayload } from "../../model/faultForm";
import { toFaultFormValues } from "../../model/faultForm";
import { validateFaultForm } from "../../model/faultForm";
import { IFaultFormValues } from "../../model/faultForm";
import { FAULT_SEVERITY_LABELS } from "@entities/fault";
import { useQueryClient } from "@tanstack/react-query";
import { EquipmentPicker } from "@entities/equipment";
import { TextFieldType } from "@shared/ui/textField";
import { useMutation } from "@tanstack/react-query";
import { FAULT_SEVERITIES } from "@entities/fault";
import { getCompanyToday } from "@shared/lib/date";
import { buildOptions } from "@shared/lib/options";
import { FlagAppearance } from "@shared/ui/flag";
import { useFormFields } from "@shared/lib/form";
import { FaultSeverity } from "@entities/fault";
import { FAULT_LIMITS } from "@entities/fault";
import { getErrorMessage } from "@shared/api";
import { createFault } from "@entities/fault";
import { updateFault } from "@entities/fault";
import { getFieldErrors } from "@shared/api";
import { hasErrors } from "@shared/lib/form";
import { faultKeys } from "@entities/fault";
import { ApiErrorCode } from "@shared/api";
import { hasErrorCode } from "@shared/api";
import { useFlags } from "@shared/ui/flag";
import { IFault } from "@entities/fault";
import { ReactElement } from "react";

interface IFaultFormModalProps {
  fault?: IFault;
  equipmentId?: string;
  onClose: () => void;
  onSaved?: (fault: IFault) => void;
}

const SEVERITY_OPTIONS = buildOptions(FAULT_SEVERITIES, FAULT_SEVERITY_LABELS);

const FaultFormModal = ({
  fault,
  equipmentId = "",
  onClose,
  onSaved,
}: IFaultFormModalProps): ReactElement => {
  const queryClient = useQueryClient();
  const { showFlag } = useFlags();
  const today: string = getCompanyToday();
  const { values, errors, setErrors, setFieldValue } =
    useFormFields<IFaultFormValues>(
      fault
        ? toFaultFormValues(fault)
        : buildInitialFaultValues(equipmentId, today)
    );
  const isEditMode: boolean = Boolean(fault);
  const patchPayload = fault ? buildFaultPatchPayload(fault, values) : null;

  const saveMutation = useMutation({
    mutationFn: () =>
      fault && patchPayload
        ? updateFault(fault, patchPayload)
        : createFault(toFaultCreatePayload(values)),
    onSuccess: (savedFault) => {
      queryClient.setQueryData(faultKeys.detail(savedFault.id), savedFault);
      queryClient.invalidateQueries({ queryKey: faultKeys.lists() });
      showFlag({
        appearance: FlagAppearance.SUCCESS,
        title: isEditMode
          ? "Неисправность обновлена"
          : "Неисправность зарегистрирована",
      });
      onSaved?.(savedFault);
      onClose();
    },
    onError: (error) => {
      setErrors((prev) => ({ ...prev, ...getFieldErrors(error) }));

      if (fault && hasErrorCode(error, ApiErrorCode.VERSION_CONFLICT)) {
        queryClient.invalidateQueries({ queryKey: faultKeys.detail(fault.id) });
      }
    },
  });

  const handleSubmit = () => {
    const validationErrors = validateFaultForm(values, today);

    setErrors(validationErrors);

    if (hasErrors(validationErrors)) return;

    saveMutation.mutate();
  };

  const updateEquipment = (value: string) => {
    setFieldValue("equipment_id", value);
  };

  const updateDescription = (value: string) => {
    setFieldValue("description", value);
  };

  const updateDetectedOn = (value: string) => {
    setFieldValue("detected_on", value);
  };

  const updateSeverity = (value: string) => {
    setFieldValue("severity", value as FaultSeverity);
  };

  const isUnchanged: boolean =
    Boolean(patchPayload) && Object.keys(patchPayload ?? {}).length === 0;

  return (
    <FormModal
      title={
        isEditMode
          ? "Редактирование неисправности"
          : "Регистрация неисправности"
      }
      submitLabel={isEditMode ? "Сохранить" : "Зарегистрировать"}
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={saveMutation.isPending}
      isSubmitDisabled={isUnchanged}
      errorMessage={
        saveMutation.isError ? getErrorMessage(saveMutation.error) : null
      }
    >
      <EquipmentPicker
        label="Оборудование"
        value={values.equipment_id}
        onChange={updateEquipment}
        errorMessage={errors.equipment_id}
        isDisabled={isEditMode || Boolean(equipmentId)}
        isRequired
      />
      <TextArea
        label="Описание неисправности"
        value={values.description}
        onChange={updateDescription}
        errorMessage={errors.description}
        helperText={`От ${FAULT_LIMITS.DESCRIPTION_MIN} до ${FAULT_LIMITS.DESCRIPTION_MAX} символов`}
        maxLength={FAULT_LIMITS.DESCRIPTION_MAX}
        isRequired
      />
      <div className="form-modal-row">
        <TextField
          label="Дата обнаружения"
          type={TextFieldType.DATE}
          value={values.detected_on}
          onChange={updateDetectedOn}
          errorMessage={errors.detected_on}
          max={today}
          isRequired
        />
        <Select
          label="Критичность"
          value={values.severity}
          options={SEVERITY_OPTIONS}
          onChange={updateSeverity}
          placeholder="Выберите критичность"
          errorMessage={errors.severity}
          isRequired
        />
      </div>
    </FormModal>
  );
};

export default FaultFormModal;
