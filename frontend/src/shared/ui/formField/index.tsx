import Icon from "@shared/ui/icon";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

interface IFormFieldProps {
  id: string;
  label: string;
  isRequired?: boolean;
  errorMessage?: string;
  helperText?: string;
  children: ReactNode;
}

export const buildDescribedBy = (
  id: string,
  errorMessage?: string,
  helperText?: string
): string | undefined => {
  if (errorMessage) return `${id}-error`;
  if (helperText) return `${id}-helper`;

  return undefined;
};

const FormField = ({
  id,
  label,
  isRequired = false,
  errorMessage,
  helperText,
  children,
}: IFormFieldProps): ReactElement => {
  return (
    <div className="form-field">
      <label className="form-field-label" htmlFor={id}>
        {label}
        {isRequired && (
          <span className="form-field-required" aria-hidden="true">
            {" *"}
          </span>
        )}
      </label>
      {children}
      {errorMessage && (
        <p className="form-field-error body-small" id={`${id}-error`}>
          <Icon name={IconName.ERROR} />
          <span>{errorMessage}</span>
        </p>
      )}
      {!errorMessage && helperText && (
        <p className="form-field-helper body-small" id={`${id}-helper`}>
          {helperText}
        </p>
      )}
    </div>
  );
};

export default FormField;
