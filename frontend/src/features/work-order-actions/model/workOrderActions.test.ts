import { buildWorkOrderFixture } from "@entities/work-order/testing";
import { hasAnyWorkOrderAction } from "./workOrderActions";
import { buildUserFixture } from "@entities/user/testing";
import { getWorkOrderActions } from "./workOrderActions";
import { WorkOrderStatus } from "@entities/work-order";
import { WorkOrderType } from "@entities/work-order";
import { UserRole } from "@entities/user";

const TECHNICIAN_ID = "tech-1";

const buildWorkOrder = (
  status: WorkOrderStatus,
  type: WorkOrderType = WorkOrderType.REPAIR
) =>
  buildWorkOrderFixture({
    status,
    type,
    schedule_id: type === WorkOrderType.PLANNED ? "schedule-1" : null,
    assignee_id: status === WorkOrderStatus.CREATED ? null : TECHNICIAN_ID,
  });

const engineer = buildUserFixture({
  id: "engineer-1",
  role: UserRole.ENGINEER,
});
const technician = buildUserFixture({
  id: TECHNICIAN_ID,
  role: UserRole.TECHNICIAN,
});
const otherTechnician = buildUserFixture({
  id: "tech-2",
  role: UserRole.TECHNICIAN,
});
const operator = buildUserFixture({
  id: "operator-1",
  role: UserRole.OPERATOR,
});

describe("work order actions", () => {
  it("allows engineer to edit, assign and cancel only CREATED orders", () => {
    const actions = getWorkOrderActions(
      engineer,
      buildWorkOrder(WorkOrderStatus.CREATED)
    );

    expect(actions).toMatchObject({
      canEdit: true,
      canAssign: true,
      canCancel: true,
      canReassign: false,
      canClose: false,
    });
  });

  it("allows engineer to reassign and cancel ASSIGNED orders without editing", () => {
    const actions = getWorkOrderActions(
      engineer,
      buildWorkOrder(WorkOrderStatus.ASSIGNED)
    );

    expect(actions).toMatchObject({
      canEdit: false,
      canAssign: false,
      canReassign: true,
      canCancel: true,
    });
  });

  it("forbids cancelling once work is in progress", () => {
    const actions = getWorkOrderActions(
      engineer,
      buildWorkOrder(WorkOrderStatus.IN_PROGRESS)
    );

    expect(actions).toMatchObject({
      canReassign: true,
      canCancel: false,
      canClose: false,
    });
  });

  it("lets only engineer close COMPLETED orders", () => {
    expect(
      getWorkOrderActions(engineer, buildWorkOrder(WorkOrderStatus.COMPLETED))
        .canClose
    ).toBe(true);
    expect(
      getWorkOrderActions(technician, buildWorkOrder(WorkOrderStatus.COMPLETED))
        .canClose
    ).toBe(false);
  });

  it("lets assigned technician start and complete, but not another technician", () => {
    expect(
      getWorkOrderActions(technician, buildWorkOrder(WorkOrderStatus.ASSIGNED))
        .canStart
    ).toBe(true);
    expect(
      getWorkOrderActions(
        otherTechnician,
        buildWorkOrder(WorkOrderStatus.ASSIGNED)
      ).canStart
    ).toBe(false);
    expect(
      getWorkOrderActions(
        technician,
        buildWorkOrder(WorkOrderStatus.IN_PROGRESS)
      ).canComplete
    ).toBe(true);
    expect(
      getWorkOrderActions(engineer, buildWorkOrder(WorkOrderStatus.IN_PROGRESS))
        .canComplete
    ).toBe(false);
  });

  it("allows checklist updates only for planned orders in progress", () => {
    const inProgressPlanned = buildWorkOrder(
      WorkOrderStatus.IN_PROGRESS,
      WorkOrderType.PLANNED
    );
    const inProgressRepair = buildWorkOrder(
      WorkOrderStatus.IN_PROGRESS,
      WorkOrderType.REPAIR
    );
    const assignedPlanned = buildWorkOrder(
      WorkOrderStatus.ASSIGNED,
      WorkOrderType.PLANNED
    );

    expect(
      getWorkOrderActions(technician, inProgressPlanned).canUpdateChecklist
    ).toBe(true);
    expect(
      getWorkOrderActions(technician, inProgressRepair).canUpdateChecklist
    ).toBe(false);
    expect(
      getWorkOrderActions(technician, assignedPlanned).canUpdateChecklist
    ).toBe(false);
  });

  it.each([WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED])(
    "keeps %s orders immutable",
    (status) => {
      expect(
        hasAnyWorkOrderAction(
          getWorkOrderActions(engineer, buildWorkOrder(status))
        )
      ).toBe(false);
      expect(
        hasAnyWorkOrderAction(
          getWorkOrderActions(technician, buildWorkOrder(status))
        )
      ).toBe(false);
    }
  );

  it.each([
    WorkOrderStatus.CREATED,
    WorkOrderStatus.ASSIGNED,
    WorkOrderStatus.COMPLETED,
  ])("gives operator no lifecycle actions for %s orders", (status) => {
    expect(
      hasAnyWorkOrderAction(
        getWorkOrderActions(operator, buildWorkOrder(status))
      )
    ).toBe(false);
  });
});
