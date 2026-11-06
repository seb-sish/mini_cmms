import { EquipmentStatus } from "./model/types";
import { IEquipment } from "./model/types";

export const buildEquipmentFixture = (
  overrides: Partial<IEquipment> = {}
): IEquipment => ({
  id: "equipment-1",
  name: "Пресс гидравлический",
  inventory_number: "INV-001",
  category: "Прессы",
  location: "Цех 1",
  commissioned_on: "2024-05-10",
  status: EquipmentStatus.OPERATIONAL,
  archived_at: null,
  version: 1,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
  ...overrides,
});
