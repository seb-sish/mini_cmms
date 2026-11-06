import { PlanScope } from "./types";

export const PLAN_SCOPE_LABELS: Record<PlanScope, string> = {
  [PlanScope.EQUIPMENT]: "Конкретное оборудование",
  [PlanScope.CATEGORY]: "Категория оборудования",
};

export const formatInterval = (intervalDays: number): string => {
  const lastDigit = intervalDays % 10;
  const lastTwoDigits = intervalDays % 100;

  if (lastDigit === 1 && lastTwoDigits !== 11) return `${intervalDays} день`;

  if (
    lastDigit >= 2 &&
    lastDigit <= 4 &&
    (lastTwoDigits < 12 || lastTwoDigits > 14)
  ) {
    return `${intervalDays} дня`;
  }

  return `${intervalDays} дней`;
};
