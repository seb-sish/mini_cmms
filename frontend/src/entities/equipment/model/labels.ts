import { LozengeAppearance } from "@shared/ui/lozenge";
import { EquipmentStatus } from "./types";

export const EQUIPMENT_STATUS_LABELS: Record<EquipmentStatus, string> = {
  [EquipmentStatus.OPERATIONAL]: "В эксплуатации",
  [EquipmentStatus.UNDER_REPAIR]: "В ремонте",
  [EquipmentStatus.OUT_OF_SERVICE]: "Выведено из работы",
};

export const EQUIPMENT_STATUS_APPEARANCES: Record<
  EquipmentStatus,
  LozengeAppearance
> = {
  [EquipmentStatus.OPERATIONAL]: LozengeAppearance.SUCCESS,
  [EquipmentStatus.UNDER_REPAIR]: LozengeAppearance.MOVED,
  [EquipmentStatus.OUT_OF_SERVICE]: LozengeAppearance.REMOVED,
};
