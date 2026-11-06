import Lozenge from "@shared/ui/lozenge";
import { getScheduleDueState } from "../../model/dueState";
import { getScheduleDueLabel } from "../../model/dueState";
import { IMaintenanceSchedule } from "../../model/types";
import { ScheduleDueState } from "../../model/dueState";
import { LozengeAppearance } from "@shared/ui/lozenge";
import { ReactElement } from "react";

interface IScheduleDueLozengeProps {
  schedule: IMaintenanceSchedule;
  today: string;
}

const DUE_STATE_APPEARANCES: Record<ScheduleDueState, LozengeAppearance> = {
  [ScheduleDueState.INACTIVE]: LozengeAppearance.DEFAULT,
  [ScheduleDueState.OVERDUE]: LozengeAppearance.REMOVED,
  [ScheduleDueState.TODAY]: LozengeAppearance.MOVED,
  [ScheduleDueState.SOON]: LozengeAppearance.MOVED,
  [ScheduleDueState.UPCOMING]: LozengeAppearance.IN_PROGRESS,
};

const ScheduleDueLozenge = ({
  schedule,
  today,
}: IScheduleDueLozengeProps): ReactElement => {
  const dueState = getScheduleDueState(schedule, today);

  return (
    <Lozenge
      label={getScheduleDueLabel(schedule, today)}
      appearance={DUE_STATE_APPEARANCES[dueState]}
      isBold={dueState === ScheduleDueState.OVERDUE}
    />
  );
};

export default ScheduleDueLozenge;
