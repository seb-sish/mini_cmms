import { ReactElement } from "react";
import "./style.css";

export const enum SpinnerSize {
  SMALL = "small",
  MEDIUM = "medium",
  LARGE = "large",
}

interface ISpinnerProps {
  size?: SpinnerSize;
  label?: string;
  isInverted?: boolean;
}

const DEFAULT_LABEL: string = "Загрузка";

const Spinner = ({
  size = SpinnerSize.MEDIUM,
  label = DEFAULT_LABEL,
  isInverted = false,
}: ISpinnerProps): ReactElement => {
  const invertedClassname: string = isInverted ? "inverted" : "";

  return (
    <span
      className={`spinner ${size} ${invertedClassname}`}
      role="status"
      aria-label={label}
    >
      <span className="spinner-circle" />
    </span>
  );
};

export default Spinner;
