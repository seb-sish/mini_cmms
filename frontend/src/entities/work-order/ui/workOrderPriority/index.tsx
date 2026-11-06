import Icon from "@shared/ui/icon";
import { WORK_ORDER_PRIORITY_LABELS } from "../../model/labels";
import { WORK_ORDER_PRIORITY_ICONS } from "../../model/labels";
import { WorkOrderPriority } from "../../model/types";
import { ReactElement } from "react";
import "./style.css";

interface IWorkOrderPriorityProps {
  priority: WorkOrderPriority;
}

const WorkOrderPriorityLabel = ({
  priority,
}: IWorkOrderPriorityProps): ReactElement => {
  return (
    <span className={`work-order-priority ${priority.toLowerCase()}`}>
      <Icon name={WORK_ORDER_PRIORITY_ICONS[priority]} />
      <span>{WORK_ORDER_PRIORITY_LABELS[priority]}</span>
    </span>
  );
};

export default WorkOrderPriorityLabel;
