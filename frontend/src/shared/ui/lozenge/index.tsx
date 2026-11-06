import { ReactElement } from "react";
import "./style.css";

export const enum LozengeAppearance {
  DEFAULT = "default",
  IN_PROGRESS = "inprogress",
  SUCCESS = "success",
  REMOVED = "removed",
  NEW = "new",
  MOVED = "moved",
}

interface ILozengeProps {
  label: string;
  appearance?: LozengeAppearance;
  isBold?: boolean;
}

const Lozenge = ({
  label,
  appearance = LozengeAppearance.DEFAULT,
  isBold = false,
}: ILozengeProps): ReactElement => {
  const boldClassname: string = isBold ? "bold" : "";

  return (
    <span className={`lozenge ${appearance} ${boldClassname}`}>{label}</span>
  );
};

export default Lozenge;
