"use client";

import Select from "@shared/ui/select";
import TextField from "@shared/ui/textField";
import FormModal from "@shared/ui/formModal";
import { buildEquipmentPatchPayload } from "../../model/equipmentForm";
import { toEquipmentCreatePayload } from "../../model/equipmentForm";
import { INITIAL_EQUIPMENT_VALUES } from "../../model/equipmentForm";
import { useEquipmentDictionariesQuery } from "@entities/equipment";
import { toEquipmentFormValues } from "../../model/equipmentForm";
import { validateEquipmentForm } from "../../model/equipmentForm";
import { EquipmentFormValues } from "../../model/equipmentForm";
import { EQUIPMENT_STATUS_LABELS } from "@entities/equipment";
import { EQUIPMENT_STATUSES } from "@entities/equipment";
import { useQueryClient } from "@tanstack/react-query";
import { EQUIPMENT_LIMITS } from "@entities/equipment";
import { createEquipment } from "@entities/equipment";
import { updateEquipment } from "@entities/equipment";
import { EquipmentStatus } from "@entities/equipment";
import { TextFieldType } from "@shared/ui/textField";
import { useMutation } from "@tanstack/react-query";
import { equipmentKeys } from "@entities/equipment";
import { getCompanyToday } from "@shared/lib/date";
import { buildOptions } from "@shared/lib/options";
import { FlagAppearance } from "@shared/ui/flag";
import { useFormFields } from "@shared/lib/form";
import { IEquipment } from "@entities/equipment";
import { getErrorMessage } from "@shared/api";
import { getFieldErrors } from "@shared/api";
import { hasErrors } from "@shared/lib/form";
import { ApiErrorCode } from "@shared/api";
import { hasErrorCode } from "@shared/api";
import { useFlags } from "@shared/ui/flag";
import { ReactElement } from "react";

interface IEquipmentFormModalProps {
  equipment?: IEquipment;
  onClose: () => void;
  onSaved?: (equipment: IEquipment) => void;
}

const STATUS_OPTIONS = buildOptions(
  EQUIPMENT_STATUSES,
  EQUIPMENT_STATUS_LABELS
);

const EquipmentFormModal = ({
  equipment,
  onClose,
  onSaved,
}: IEquipmentFormModalProps): ReactElement => {
  const queryClient = useQueryClient();
  const { showFlag } = useFlags();
  const { data: dictionaries } = useEquipmentDictionariesQuery();
  const { values, errors, setErrors, setFieldValue } =
    useFormFields<EquipmentFormValues>(
      equipment ? toEquipmentFormValues(equipment) : INITIAL_EQUIPMENT_VALUES
    );
  const today: string = getCompanyToday();
  const isEditMode: boolean = Boolean(equipment);
  const patchPayload = equipment
    ? buildEquipmentPatchPayload(equipment, values)
    : null;

  const saveMutation = useMutation({
    mutationFn: () =>
      equipment && patchPayload
        ? updateEquipment(equipment, patchPayload)
        : createEquipment(toEquipmentCreatePayload(values)),
    onSuccess: (savedEquipment) => {
      queryClient.setQueryData(
        equipmentKeys.detail(savedEquipment.id),
        savedEquipment
      );
      queryClient.invalidateQueries({ queryKey: equipmentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: equipmentKeys.dictionaries() });
      showFlag({
        appearance: FlagAppearance.SUCCESS,
        title: isEditMode
          ? "Карточка оборудования сохранена"
          : "Оборудование добавлено",
        description: savedEquipment.name,
      });
      onSaved?.(savedEquipment);
      onClose();
    },
    onError: (error) => {
      setErrors((prev) => ({
        ...prev,
        ...getFieldErrors(error),
        inventory_number: hasErrorCode(
          error,
          ApiErrorCode.DUPLICATE_INVENTORY_NUMBER
        )
          ? "Этот инвентарный номер уже используется."
          : prev.inventory_number,
      }));

      if (equipment && hasErrorCode(error, ApiErrorCode.VERSION_CONFLICT)) {
        queryClient.invalidateQueries({
          queryKey: equipmentKeys.detail(equipment.id),
        });
      }
    },
  });

  const handleSubmit = () => {
    const validationErrors = validateEquipmentForm(values, today);

    setErrors(validationErrors);

    if (hasErrors(validationErrors)) return;

    saveMutation.mutate();
  };

  const updateName = (value: string) => {
    setFieldValue("name", value);
  };

  const updateInventoryNumber = (value: string) => {
    setFieldValue("inventory_number", value);
  };

  const updateCategory = (value: string) => {
    setFieldValue("category", value);
  };

  const updateLocation = (value: string) => {
    setFieldValue("location", value);
  };

  const updateCommissionedOn = (value: string) => {
    setFieldValue("commissioned_on", value);
  };

  const updateStatus = (value: string) => {
    setFieldValue("status", value as EquipmentStatus);
  };

  const isUnchanged: boolean =
    Boolean(patchPayload) && Object.keys(patchPayload ?? {}).length === 0;

  return (
    <FormModal
      title={isEditMode ? "Редактирование оборудования" : "Новое оборудование"}
      submitLabel={isEditMode ? "Сохранить" : "Добавить"}
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={saveMutation.isPending}
      isSubmitDisabled={isUnchanged}
      errorMessage={
        saveMutation.isError ? getErrorMessage(saveMutation.error) : null
      }
    >
      <TextField
        label="Наименование"
        value={values.name}
        onChange={updateName}
        errorMessage={errors.name}
        maxLength={EQUIPMENT_LIMITS.NAME_MAX}
        isRequired
      />
      <div className="form-modal-row">
        <TextField
          label="Инвентарный номер"
          value={values.inventory_number}
          onChange={updateInventoryNumber}
          errorMessage={errors.inventory_number}
          helperText="Уникален, включая архивное оборудование"
          maxLength={EQUIPMENT_LIMITS.INVENTORY_NUMBER_MAX}
          isRequired
        />
        <TextField
          label="Дата ввода в эксплуатацию"
          type={TextFieldType.DATE}
          value={values.commissioned_on}
          onChange={updateCommissionedOn}
          errorMessage={errors.commissioned_on}
          max={today}
          isRequired
        />
      </div>
      <div className="form-modal-row">
        <TextField
          label="Категория"
          value={values.category}
          onChange={updateCategory}
          errorMessage={errors.category}
          helperText="Выберите из списка или введите новую"
          maxLength={EQUIPMENT_LIMITS.CATEGORY_MAX}
          suggestions={dictionaries?.categories}
          isRequired
        />
        <TextField
          label="Цех / местоположение"
          value={values.location}
          onChange={updateLocation}
          errorMessage={errors.location}
          maxLength={EQUIPMENT_LIMITS.LOCATION_MAX}
          suggestions={dictionaries?.locations}
          isRequired
        />
      </div>
      <Select
        label="Статус"
        value={values.status}
        options={STATUS_OPTIONS}
        onChange={updateStatus}
        helperText={
          isEditMode
            ? "Смена статуса не закрывает неисправности автоматически"
            : undefined
        }
        isRequired
      />
    </FormModal>
  );
};

export default EquipmentFormModal;
