export const enum EquipmentStatus {
  OPERATIONAL = "OPERATIONAL",
  UNDER_REPAIR = "UNDER_REPAIR",
  OUT_OF_SERVICE = "OUT_OF_SERVICE",
}

export interface IEquipment {
  id: string;
  name: string;
  inventory_number: string;
  category: string;
  location: string;
  commissioned_on: string;
  status: EquipmentStatus;
  archived_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface IEquipmentCreatePayload {
  name: string;
  inventory_number: string;
  category: string;
  location: string;
  commissioned_on: string;
  status: EquipmentStatus;
}

export type EquipmentPatchPayload = Partial<IEquipmentCreatePayload>;

export interface IEquipmentListParams {
  limit: number;
  offset: number;
  q?: string;
  category?: string;
  location?: string;
  status?: EquipmentStatus | "";
  include_archived?: boolean;
  is_archived?: boolean;
}

export const EQUIPMENT_STATUSES: readonly EquipmentStatus[] = [
  EquipmentStatus.OPERATIONAL,
  EquipmentStatus.UNDER_REPAIR,
  EquipmentStatus.OUT_OF_SERVICE,
];

export const EQUIPMENT_LIMITS = {
  NAME_MAX: 200,
  INVENTORY_NUMBER_MAX: 64,
  CATEGORY_MAX: 100,
  LOCATION_MAX: 200,
} as const;

export const isEquipmentArchived = (equipment: IEquipment): boolean =>
  equipment.archived_at !== null;
