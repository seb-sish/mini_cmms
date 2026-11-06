import { LozengeAppearance } from "@shared/ui/lozenge";
import { UserStatus } from "./types";
import { UserRole } from "./types";

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  [UserRole.ADMIN]: "Администратор",
  [UserRole.ENGINEER]: "Главный инженер",
  [UserRole.TECHNICIAN]: "Техник",
  [UserRole.OPERATOR]: "Оператор",
};

export const USER_STATUS_LABELS: Record<UserStatus, string> = {
  [UserStatus.ACTIVE]: "Активен",
  [UserStatus.BLOCKED]: "Заблокирован",
};

export const USER_STATUS_APPEARANCES: Record<UserStatus, LozengeAppearance> = {
  [UserStatus.ACTIVE]: LozengeAppearance.SUCCESS,
  [UserStatus.BLOCKED]: LozengeAppearance.REMOVED,
};
