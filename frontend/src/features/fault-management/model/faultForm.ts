import { IFaultCreatePayload } from "@entities/fault";
import { IFaultPatchPayload } from "@entities/fault";
import { normalizeText } from "@shared/lib/form";
import { FaultSeverity } from "@entities/fault";
import { validateText } from "@shared/lib/form";
import { validateDate } from "@shared/lib/form";
import { FAULT_LIMITS } from "@entities/fault";
import { FaultStatus } from "@entities/fault";
import { FormErrors } from "@shared/lib/form";
import { UserRole } from "@entities/user";
import { IFault } from "@entities/fault";
import { IUser } from "@entities/user";

export interface IFaultFormValues {
  equipment_id: string;
  description: string;
  detected_on: string;
  severity: FaultSeverity | "";
}

export const buildInitialFaultValues = (
  equipmentId: string,
  today: string
): IFaultFormValues => ({
  equipment_id: equipmentId,
  description: "",
  detected_on: today,
  severity: "",
});

export const toFaultFormValues = (fault: IFault): IFaultFormValues => ({
  equipment_id: fault.equipment_id,
  description: fault.description,
  detected_on: fault.detected_on,
  severity: fault.severity,
});

export const validateFaultForm = (
  values: IFaultFormValues,
  today: string
): FormErrors<IFaultFormValues> => ({
  equipment_id: values.equipment_id ? undefined : "Выберите оборудование.",
  description: validateText(values.description, {
    isRequired: true,
    minLength: FAULT_LIMITS.DESCRIPTION_MIN,
    maxLength: FAULT_LIMITS.DESCRIPTION_MAX,
  }),
  detected_on: validateDate(values.detected_on, {
    isRequired: true,
    notAfter: today,
  }),
  severity: values.severity ? undefined : "Выберите критичность.",
});

export const toFaultCreatePayload = (
  values: IFaultFormValues
): IFaultCreatePayload => ({
  equipment_id: values.equipment_id,
  description: normalizeText(values.description),
  detected_on: values.detected_on,
  severity: values.severity as FaultSeverity,
});

export const buildFaultPatchPayload = (
  fault: IFault,
  values: IFaultFormValues
): IFaultPatchPayload => {
  const payload: IFaultPatchPayload = {};
  const description = normalizeText(values.description);

  if (description !== fault.description) payload.description = description;
  if (values.detected_on !== fault.detected_on)
    payload.detected_on = values.detected_on;
  if (values.severity && values.severity !== fault.severity)
    payload.severity = values.severity;

  return payload;
};

export const canEditFault = (viewer: IUser, fault: IFault): boolean => {
  if (fault.status !== FaultStatus.OPEN) return false;

  if (viewer.role === UserRole.ENGINEER) return true;

  return viewer.role === UserRole.OPERATOR && fault.author_id === viewer.id;
};
