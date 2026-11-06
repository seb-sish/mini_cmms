import { LozengeAppearance } from "@shared/ui/lozenge";
import { NotificationType } from "./types";

export const NOTIFICATION_TYPE_LABELS: Record<NotificationType, string> = {
  [NotificationType.THREE_DAYS_BEFORE]: "За 3 дня",
  [NotificationType.ON_DUE_DATE]: "В день ТО",
};

export const NOTIFICATION_TYPE_APPEARANCES: Record<
  NotificationType,
  LozengeAppearance
> = {
  [NotificationType.THREE_DAYS_BEFORE]: LozengeAppearance.MOVED,
  [NotificationType.ON_DUE_DATE]: LozengeAppearance.REMOVED,
};
