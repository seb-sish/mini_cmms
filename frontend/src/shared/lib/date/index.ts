import { COMPANY_TIMEZONE } from "@shared/config";

const MS_IN_DAY = 24 * 60 * 60 * 1000;
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const toUtcDate = (isoDate: string): Date => new Date(`${isoDate}T00:00:00Z`);

const toIsoDate = (date: Date): string => date.toISOString().slice(0, 10);

export const isIsoDate = (value: string): boolean =>
  ISO_DATE_PATTERN.test(value) &&
  !Number.isNaN(toUtcDate(value).getTime()) &&
  toIsoDate(toUtcDate(value)) === value;

export const formatDate = (isoDate: string): string => {
  const [year, month, day] = isoDate.split("-");

  return `${day}.${month}.${year}`;
};

export const formatDateTime = (
  timestamp: string,
  timeZone: string = COMPANY_TIMEZONE
): string =>
  new Intl.DateTimeFormat("ru-RU", {
    timeZone,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));

export const getCompanyToday = (
  now: Date = new Date(),
  timeZone: string = COMPANY_TIMEZONE
): string =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);

export const toCompanyDate = (
  timestamp: string,
  timeZone: string = COMPANY_TIMEZONE
): string => getCompanyToday(new Date(timestamp), timeZone);

export const addDays = (isoDate: string, days: number): string => {
  const date = toUtcDate(isoDate);

  date.setUTCDate(date.getUTCDate() + days);

  return toIsoDate(date);
};

export const diffInDays = (
  fromIsoDate: string,
  toIsoDateValue: string
): number =>
  Math.round(
    (toUtcDate(toIsoDateValue).getTime() - toUtcDate(fromIsoDate).getTime()) /
      MS_IN_DAY
  );

export const isDateAfter = (left: string, right: string): boolean =>
  left > right;
