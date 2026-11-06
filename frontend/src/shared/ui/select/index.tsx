"use client";

import FormField from "@shared/ui/formField";
import { buildDescribedBy } from "@shared/ui/formField";
import { classNames } from "@shared/lib/classNames";
import { ISelectOption } from "@shared/lib/options";
import { ReactElement } from "react";
import { ChangeEvent } from "react";
import { useId } from "react";
import "./style.css";

interface ISelectProps {
  label: string;
  value: string;
  options: ISelectOption[];
  onChange: (value: string) => void;
  name?: string;
  placeholder?: string;
  isRequired?: boolean;
  isDisabled?: boolean;
  errorMessage?: string;
  helperText?: string;
}

const Select = ({
  label,
  value,
  options,
  onChange,
  name,
  placeholder,
  isRequired = false,
  isDisabled = false,
  errorMessage,
  helperText,
}: ISelectProps): ReactElement => {
  const id = useId();

  const onHandleChange = (event: ChangeEvent<HTMLSelectElement>) => {
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
      <select
        id={id}
        className={classNames(
          "form-control",
          "select",
          Boolean(errorMessage) && "invalid"
        )}
        name={name}
        value={value}
        required={isRequired}
        disabled={isDisabled}
        aria-invalid={Boolean(errorMessage)}
        aria-describedby={buildDescribedBy(id, errorMessage, helperText)}
        onChange={onHandleChange}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FormField>
  );
};

export default Select;
