export type ClassNameValue = string | false | null | undefined;

export const classNames = (...values: ClassNameValue[]): string =>
  values.filter(Boolean).join(" ");
