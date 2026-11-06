import Lozenge from "@shared/ui/lozenge";
import { WORK_ORDER_STATUS_APPEARANCES } from "../../model/labels";
import { WORK_ORDER_STATUS_LABELS } from "../../model/labels";
import { WorkOrderStatus } from "../../model/types";
import { ReactElement } from "react";

interface IWorkOrderStatusLozengeProps {
  status: WorkOrderStatus;
  isBold?: boolean;
}

const WorkOrderStatusLozenge = ({
  status,
  isBold = false,
}: IWorkOrderStatusLozengeProps): ReactElement => {
  return (
    <Lozenge
      label={WORK_ORDER_STATUS_LABELS[status]}
      appearance={WORK_ORDER_STATUS_APPEARANCES[status]}
      isBold={isBold}
    />
  );
};

export default WorkOrderStatusLozenge;
