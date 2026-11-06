import { FaultSeverity } from "./model/types";
import { FaultStatus } from "./model/types";
import { IFault } from "./model/types";

export const buildFaultFixture = (overrides: Partial<IFault> = {}): IFault => ({
  id: "fault-1",
  equipment_id: "equipment-1",
  description: "Посторонний шум в подшипнике",
  detected_on: "2026-10-28",
  severity: FaultSeverity.HIGH,
  status: FaultStatus.OPEN,
  author_id: "operator-1",
  version: 1,
  created_at: "2026-10-28T08:00:00Z",
  updated_at: "2026-10-28T08:00:00Z",
  ...overrides,
});
