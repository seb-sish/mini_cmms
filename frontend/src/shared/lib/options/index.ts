export interface ISelectOption {
  value: string;
  label: string;
}

export const buildOptions = <TValue extends string>(
  values: readonly TValue[],
  labels: Record<TValue, string>
): ISelectOption[] => values.map((value) => ({ value, label: labels[value] }));

export const shortenId = (id: string): string => id.slice(0, 8);
