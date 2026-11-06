import Icon from "@shared/ui/icon";
import { IconName } from "@shared/ui/icon";
import { IconSize } from "@shared/ui/icon";
import { ReactElement } from "react";
import "./style.css";

export const enum ProgressStepState {
  DONE = "done",
  CURRENT = "current",
  UPCOMING = "upcoming",
}

export interface IProgressStep {
  id: string;
  label: string;
  state: ProgressStepState;
}

interface IProgressTrackerProps {
  label: string;
  steps: IProgressStep[];
}

const ProgressTracker = ({
  label,
  steps,
}: IProgressTrackerProps): ReactElement => {
  return (
    <ol className="progress-tracker" aria-label={label}>
      {steps.map((step) => (
        <li
          key={step.id}
          className={`progress-tracker-step ${step.state}`}
          aria-current={
            step.state === ProgressStepState.CURRENT ? "step" : undefined
          }
        >
          <span className="progress-tracker-marker">
            {step.state === ProgressStepState.DONE && (
              <Icon name={IconName.CHECK} size={IconSize.SMALL} />
            )}
          </span>
          <span className="progress-tracker-label body-small">
            {step.label}
          </span>
        </li>
      ))}
    </ol>
  );
};

export default ProgressTracker;
