"use client";

import { ReactElement } from "react";
import { ChangeEvent } from "react";
import { useId } from "react";
import "./style.css";

interface ICheckboxProps {
  label: string;
  isChecked: boolean;
  onChange: (isChecked: boolean) => void;
  description?: string;
  isDisabled?: boolean;
  isRequired?: boolean;
}

const Checkbox = ({
  label,
  isChecked,
  onChange,
  description,
  isDisabled = false,
  isRequired = false,
}: ICheckboxProps): ReactElement => {
  const id = useId();

  const onHandleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.checked);
  };

  const disabledClassname: string = isDisabled ? "disabled" : "";

  return (
    <div className={`checkbox ${disabledClassname}`}>
      <input
        id={id}
        className="checkbox-input"
        type="checkbox"
        checked={isChecked}
        disabled={isDisabled}
        aria-describedby={description ? `${id}-description` : undefined}
        onChange={onHandleChange}
      />
      <label className="checkbox-label" htmlFor={id}>
        <span>
          {label}
          {isRequired && (
            <span className="checkbox-required" aria-label="обязательный пункт">
              {" *"}
            </span>
          )}
        </span>
        {description && (
          <span
            className="checkbox-description body-small"
            id={`${id}-description`}
          >
            {description}
          </span>
        )}
      </label>
    </div>
  );
};

export default Checkbox;
