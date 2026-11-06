import ProgressTracker from "@shared/ui/progressTracker";
import { ProgressStepState } from "@shared/ui/progressTracker";
import { WORK_ORDER_STATUS_LABELS } from "../../model/labels";
import { IProgressStep } from "@shared/ui/progressTracker";
import { WORKFLOW_STATUSES } from "../../model/lifecycle";
import { WorkOrderStatus } from "../../model/types";
import { ReactElement } from "react";

interface IWorkOrderStatusTrackerProps {
  status: WorkOrderStatus;
}

export const buildWorkflowSteps = (
  status: WorkOrderStatus
): IProgressStep[] => {
  const currentIndex = WORKFLOW_STATUSES.indexOf(status);

  return WORKFLOW_STATUSES.map((workflowStatus, index) => {
    let state: ProgressStepState = ProgressStepState.UPCOMING;

    if (index < currentIndex || status === WorkOrderStatus.CLOSED)
      state = ProgressStepState.DONE;
    else if (index === currentIndex) state = ProgressStepState.CURRENT;

    return {
      id: workflowStatus,
      label: WORK_ORDER_STATUS_LABELS[workflowStatus],
      state,
    };
  });
};

const WorkOrderStatusTracker = ({
  status,
}: IWorkOrderStatusTrackerProps): ReactElement | null => {
  if (status === WorkOrderStatus.CANCELLED) return null;

  return (
    <ProgressTracker label="Этапы заявки" steps={buildWorkflowSteps(status)} />
  );
};

export default WorkOrderStatusTracker;
