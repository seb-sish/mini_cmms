import WorkOrderStatusTracker from "./index";
import { ProgressStepState } from "@shared/ui/progressTracker";
import { WorkOrderStatus } from "../../model/types";
import { render } from "@testing-library/react";
import { buildWorkflowSteps } from "./index";

describe("WorkOrderStatusTracker", () => {
  it("marks previous steps done and current step active", () => {
    const states = buildWorkflowSteps(WorkOrderStatus.IN_PROGRESS).map(
      (step) => step.state
    );

    expect(states).toEqual([
      ProgressStepState.DONE,
      ProgressStepState.DONE,
      ProgressStepState.CURRENT,
      ProgressStepState.UPCOMING,
      ProgressStepState.UPCOMING,
    ]);
  });

  it("marks every step done for closed orders", () => {
    expect(
      buildWorkflowSteps(WorkOrderStatus.CLOSED).every(
        (step) => step.state === ProgressStepState.DONE
      )
    ).toBe(true);
  });

  it("is hidden for cancelled orders", () => {
    const { container } = render(
      <WorkOrderStatusTracker status={WorkOrderStatus.CANCELLED} />
    );

    expect(container).toBeEmptyDOMElement();
  });
});
