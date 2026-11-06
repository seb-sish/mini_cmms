"use client";

import Icon from "@shared/ui/icon";
import Spinner from "@shared/ui/spinner";
import { classNames } from "@shared/lib/classNames";
import { SpinnerSize } from "@shared/ui/spinner";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import "./style.css";

export const enum ButtonAppearance {
  DEFAULT = "default",
  PRIMARY = "primary",
  SUBTLE = "subtle",
  WARNING = "warning",
  DANGER = "danger",
  LINK = "link",
}

export const enum ButtonSpacing {
  DEFAULT = "spacing-default",
  COMPACT = "spacing-compact",
}

export const enum ButtonType {
  BUTTON = "button",
  SUBMIT = "submit",
}

interface IButtonProps {
  label: string;
  appearance?: ButtonAppearance;
  spacing?: ButtonSpacing;
  type?: ButtonType;
  iconBefore?: IconName;
  isIconOnly?: boolean;
  isDisabled?: boolean;
  isLoading?: boolean;
  isSelected?: boolean;
  shouldFitContainer?: boolean;
  form?: string;
  onClick?: () => void;
}

const Button = ({
  label,
  appearance = ButtonAppearance.DEFAULT,
  spacing = ButtonSpacing.DEFAULT,
  type = ButtonType.BUTTON,
  iconBefore,
  isIconOnly = false,
  isDisabled = false,
  isLoading = false,
  isSelected = false,
  shouldFitContainer = false,
  form,
  onClick,
}: IButtonProps): ReactElement => {
  const isInvertedSpinner: boolean =
    appearance === ButtonAppearance.PRIMARY ||
    appearance === ButtonAppearance.DANGER;

  return (
    <button
      className={classNames(
        "button",
        appearance,
        spacing,
        isIconOnly && "icon-only",
        isSelected && "selected",
        isLoading && "loading",
        shouldFitContainer && "fit-container"
      )}
      type={type}
      form={form}
      disabled={isDisabled || isLoading}
      aria-busy={isLoading}
      aria-label={isIconOnly ? label : undefined}
      title={isIconOnly ? label : undefined}
      onClick={onClick}
    >
      {iconBefore && <Icon name={iconBefore} />}
      {!isIconOnly && <span className="button-label">{label}</span>}
      {isLoading && (
        <span className="button-spinner">
          <Spinner size={SpinnerSize.SMALL} isInverted={isInvertedSpinner} />
        </span>
      )}
    </button>
  );
};

export default Button;
