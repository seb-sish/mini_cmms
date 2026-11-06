import { LozengeAppearance } from "@shared/ui/lozenge";
import { FaultSeverity } from "./types";
import { FaultStatus } from "./types";

export const FAULT_SEVERITY_LABELS: Record<FaultSeverity, string> = {
  [FaultSeverity.LOW]: "Низкая",
  [FaultSeverity.MEDIUM]: "Средняя",
  [FaultSeverity.HIGH]: "Высокая",
  [FaultSeverity.CRITICAL]: "Критическая",
};

export const FAULT_SEVERITY_APPEARANCES: Record<
  FaultSeverity,
  LozengeAppearance
> = {
  [FaultSeverity.LOW]: LozengeAppearance.DEFAULT,
  [FaultSeverity.MEDIUM]: LozengeAppearance.MOVED,
  [FaultSeverity.HIGH]: LozengeAppearance.REMOVED,
  [FaultSeverity.CRITICAL]: LozengeAppearance.REMOVED,
};

export const FAULT_STATUS_LABELS: Record<FaultStatus, string> = {
  [FaultStatus.OPEN]: "Открыта",
  [FaultStatus.IN_PROGRESS]: "В работе",
  [FaultStatus.RESOLVED]: "Устранена",
};

export const FAULT_STATUS_APPEARANCES: Record<FaultStatus, LozengeAppearance> =
  {
    [FaultStatus.OPEN]: LozengeAppearance.NEW,
    [FaultStatus.IN_PROGRESS]: LozengeAppearance.IN_PROGRESS,
    [FaultStatus.RESOLVED]: LozengeAppearance.SUCCESS,
  };
