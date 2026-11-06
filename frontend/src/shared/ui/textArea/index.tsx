"use client";

import FormField from "@shared/ui/formField";
import { buildDescribedBy } from "@shared/ui/formField";
import { classNames } from "@shared/lib/classNames";
import { ReactElement } from "react";
import { ChangeEvent } from "react";
import { useId } from "react";
import "./style.css";

interface ITextAreaProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  name?: string;
  placeholder?: string;
  rows?: number;
  isRequired?: boolean;
  isDisabled?: boolean;
  errorMessage?: string;
  helperText?: string;
  maxLength?: number;
}

const DEFAULT_ROWS = 4;

const TextArea = ({
  label,
  value,
  onChange,
  name,
  placeholder,
  rows = DEFAULT_ROWS,
  isRequired = false,
  isDisabled = false,
  errorMessage,
  helperText,
  maxLength,
}: ITextAreaProps): ReactElement => {
  const id = useId();

  const onHandleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
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
      <textarea
        id={id}
        className={classNames(
          "form-control",
          "text-area",
          Boolean(errorMessage) && "invalid"
        )}
        name={name}
        value={value}
        placeholder={placeholder}
        rows={rows}
        required={isRequired}
        disabled={isDisabled}
        maxLength={maxLength}
        aria-invalid={Boolean(errorMessage)}
        aria-describedby={buildDescribedBy(id, errorMessage, helperText)}
        onChange={onHandleChange}
      />
    </FormField>
  );
};

export default TextArea;
