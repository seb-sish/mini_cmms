"use client";

import FormField from "@shared/ui/formField";
import { buildDescribedBy } from "@shared/ui/formField";
import { classNames } from "@shared/lib/classNames";
import { ReactElement } from "react";
import { ChangeEvent } from "react";
import { useId } from "react";

export const enum TextFieldType {
  TEXT = "text",
  PASSWORD = "password",
  DATE = "date",
  NUMBER = "number",
}

interface ITextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  name?: string;
  type?: TextFieldType;
  placeholder?: string;
  isRequired?: boolean;
  isDisabled?: boolean;
  errorMessage?: string;
  helperText?: string;
  maxLength?: number;
  min?: string;
  max?: string;
  autoComplete?: string;
  autoFocus?: boolean;
  suggestions?: string[];
}

const TextField = ({
  label,
  value,
  onChange,
  name,
  type = TextFieldType.TEXT,
  placeholder,
  isRequired = false,
  isDisabled = false,
  errorMessage,
  helperText,
  maxLength,
  min,
  max,
  autoComplete,
  autoFocus,
  suggestions,
}: ITextFieldProps): ReactElement => {
  const id = useId();
  const suggestionsId: string | undefined =
    suggestions && suggestions.length > 0 ? `${id}-suggestions` : undefined;

  const onHandleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value);
  };

  return (
    <FormField
      id={id}
      label={label}
      isRequired={isRequired}
      errorMessage={errorMessage}
      helperText={helperText}
    >
      <input
        id={id}
        className={classNames(
          "form-control",
          Boolean(errorMessage) && "invalid"
        )}
        name={name}
        type={type}
        value={value}
        placeholder={placeholder}
        required={isRequired}
        disabled={isDisabled}
        maxLength={maxLength}
        min={min}
        max={max}
        autoComplete={autoComplete}
        autoFocus={autoFocus}
        aria-invalid={Boolean(errorMessage)}
        aria-describedby={buildDescribedBy(id, errorMessage, helperText)}
        list={suggestionsId}
        onChange={onHandleChange}
      />
      {suggestionsId && (
        <datalist id={suggestionsId}>
          {suggestions?.map((suggestion) => (
            <option key={suggestion} value={suggestion} />
          ))}
        </datalist>
      )}
    </FormField>
  );
};

export default TextField;
