import Lozenge from "@shared/ui/lozenge";
import { FAULT_SEVERITY_APPEARANCES } from "../../model/labels";
import { FAULT_SEVERITY_LABELS } from "../../model/labels";
import { FaultSeverity } from "../../model/types";
import { ReactElement } from "react";

interface IFaultSeverityLozengeProps {
  severity: FaultSeverity;
}

const FaultSeverityLozenge = ({
  severity,
}: IFaultSeverityLozengeProps): ReactElement => {
  return (
    <Lozenge
      label={FAULT_SEVERITY_LABELS[severity]}
      appearance={FAULT_SEVERITY_APPEARANCES[severity]}
      isBold={severity === FaultSeverity.CRITICAL}
    />
  );
};

export default FaultSeverityLozenge;
