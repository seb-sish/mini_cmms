import { isIsoDate } from "@shared/lib/date";

export type FormErrors<TValues> = Partial<Record<keyof TValues, string>>;

interface ITextRule {
  isRequired?: boolean;
  minLength?: number;
  maxLength?: number;
}

export const REQUIRED_MESSAGE: string = "Обязательное поле.";

export const isBlank = (value: string): boolean => value.trim().length === 0;

export const normalizeText = (value: string): string => value.trim();

export const validateText = (
  value: string,
  { isRequired = false, minLength, maxLength }: ITextRule
): string | undefined => {
  const normalizedValue = normalizeText(value);

  if (!normalizedValue) return isRequired ? REQUIRED_MESSAGE : undefined;

  if (minLength !== undefined && normalizedValue.length < minLength) {
    return `Минимальная длина: ${minLength} симв.`;
  }

  if (maxLength !== undefined && normalizedValue.length > maxLength) {
    return `Максимальная длина: ${maxLength} симв.`;
  }

  return undefined;
};

export const validatePassword = (
  value: string,
  { minLength, maxLength }: { minLength: number; maxLength: number }
): string | undefined => {
  if (!value) return REQUIRED_MESSAGE;

  if (value.length < minLength) return `Минимальная длина: ${minLength} симв.`;

  if (value.length > maxLength) return `Максимальная длина: ${maxLength} симв.`;

  return undefined;
};

export const validateDate = (
  value: string,
  { isRequired = false, notAfter }: { isRequired?: boolean; notAfter?: string }
): string | undefined => {
  if (!value) return isRequired ? REQUIRED_MESSAGE : undefined;

  if (!isIsoDate(value)) return "Некорректная дата.";

  if (notAfter && value > notAfter)
    return "Дата не может быть позже сегодняшней.";

  return undefined;
};

export const validateIntegerRange = (
  value: string,
  { min, max }: { min: number; max: number }
): string | undefined => {
  if (!value.trim()) return REQUIRED_MESSAGE;

  const numberValue = Number(value);

  if (!Number.isInteger(numberValue)) return "Введите целое число.";

  if (numberValue < min || numberValue > max)
    return `Допустимо от ${min} до ${max}.`;

  return undefined;
};

export const hasErrors = <TValues>(errors: FormErrors<TValues>): boolean =>
  Object.values(errors).some(Boolean);
