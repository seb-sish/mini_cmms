import { IEquipmentCreatePayload } from "@entities/equipment";
import { EquipmentPatchPayload } from "@entities/equipment";
import { EQUIPMENT_LIMITS } from "@entities/equipment";
import { EquipmentStatus } from "@entities/equipment";
import { normalizeText } from "@shared/lib/form";
import { IEquipment } from "@entities/equipment";
import { validateText } from "@shared/lib/form";
import { validateDate } from "@shared/lib/form";
import { FormErrors } from "@shared/lib/form";

export type EquipmentFormValues = IEquipmentCreatePayload;

export const INITIAL_EQUIPMENT_VALUES: EquipmentFormValues = {
  name: "",
  inventory_number: "",
  category: "",
  location: "",
  commissioned_on: "",
  status: EquipmentStatus.OPERATIONAL,
};

export const toEquipmentFormValues = (
  equipment: IEquipment
): EquipmentFormValues => ({
  name: equipment.name,
  inventory_number: equipment.inventory_number,
  category: equipment.category,
  location: equipment.location,
  commissioned_on: equipment.commissioned_on,
  status: equipment.status,
});

export const validateEquipmentForm = (
  values: EquipmentFormValues,
  today: string
): FormErrors<EquipmentFormValues> => ({
  name: validateText(values.name, {
    isRequired: true,
    maxLength: EQUIPMENT_LIMITS.NAME_MAX,
  }),
  inventory_number: validateText(values.inventory_number, {
    isRequired: true,
    maxLength: EQUIPMENT_LIMITS.INVENTORY_NUMBER_MAX,
  }),
  category: validateText(values.category, {
    isRequired: true,
    maxLength: EQUIPMENT_LIMITS.CATEGORY_MAX,
  }),
  location: validateText(values.location, {
    isRequired: true,
    maxLength: EQUIPMENT_LIMITS.LOCATION_MAX,
  }),
  commissioned_on: validateDate(values.commissioned_on, {
    isRequired: true,
    notAfter: today,
  }),
});

export const toEquipmentCreatePayload = (
  values: EquipmentFormValues
): IEquipmentCreatePayload => ({
  name: normalizeText(values.name),
  inventory_number: normalizeText(values.inventory_number),
  category: normalizeText(values.category),
  location: normalizeText(values.location),
  commissioned_on: values.commissioned_on,
  status: values.status,
});

export const buildEquipmentPatchPayload = (
  equipment: IEquipment,
  values: EquipmentFormValues
): EquipmentPatchPayload => {
  const nextValues = toEquipmentCreatePayload(values);
  const currentValues = toEquipmentFormValues(equipment);

  return (
    Object.keys(nextValues) as (keyof EquipmentFormValues)[]
  ).reduce<EquipmentPatchPayload>(
    (payload, key) =>
      nextValues[key] === currentValues[key]
        ? payload
        : { ...payload, [key]: nextValues[key] },
    {}
  );
};
