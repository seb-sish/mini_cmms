import Lozenge from "@shared/ui/lozenge";
import { FAULT_STATUS_APPEARANCES } from "../../model/labels";
import { FAULT_STATUS_LABELS } from "../../model/labels";
import { FaultStatus } from "../../model/types";
import { ReactElement } from "react";

interface IFaultStatusLozengeProps {
  status: FaultStatus;
}

const FaultStatusLozenge = ({
  status,
}: IFaultStatusLozengeProps): ReactElement => {
  return (
    <Lozenge
      label={FAULT_STATUS_LABELS[status]}
      appearance={FAULT_STATUS_APPEARANCES[status]}
    />
  );
};

export default FaultStatusLozenge;
