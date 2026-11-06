import { IMaintenanceSchedule } from "./types";
import { diffInDays } from "@shared/lib/date";

export const enum ScheduleDueState {
  INACTIVE = "inactive",
  OVERDUE = "overdue",
  TODAY = "today",
  SOON = "soon",
  UPCOMING = "upcoming",
}

export const REMINDER_WINDOW_DAYS: number = 3;

export const getScheduleDueState = (
  schedule: IMaintenanceSchedule,
  today: string
): ScheduleDueState => {
  if (!schedule.active) return ScheduleDueState.INACTIVE;
  if (schedule.is_overdue) return ScheduleDueState.OVERDUE;

  const daysLeft = diffInDays(today, schedule.next_due_on);

  if (daysLeft <= 0) return ScheduleDueState.TODAY;
  if (daysLeft <= REMINDER_WINDOW_DAYS) return ScheduleDueState.SOON;

  return ScheduleDueState.UPCOMING;
};

export const getScheduleDueLabel = (
  schedule: IMaintenanceSchedule,
  today: string
): string => {
  const daysLeft = diffInDays(today, schedule.next_due_on);

  switch (getScheduleDueState(schedule, today)) {
    case ScheduleDueState.INACTIVE:
      return "Неактивен";
    case ScheduleDueState.OVERDUE:
      return daysLeft < 0
        ? `Просрочено на ${Math.abs(daysLeft)} дн.`
        : "Просрочено";
    case ScheduleDueState.TODAY:
      return "Сегодня";
    default:
      return `Через ${daysLeft} дн.`;
  }
};
