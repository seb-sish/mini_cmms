import Lozenge from "@shared/ui/lozenge";
import { LozengeAppearance } from "@shared/ui/lozenge";
import { ReactElement } from "react";

interface IPlanEnabledLozengeProps {
  isEnabled: boolean;
}

const PlanEnabledLozenge = ({
  isEnabled,
}: IPlanEnabledLozengeProps): ReactElement => {
  return (
    <Lozenge
      label={isEnabled ? "Включён" : "На паузе"}
      appearance={
        isEnabled ? LozengeAppearance.SUCCESS : LozengeAppearance.DEFAULT
      }
    />
  );
};

export default PlanEnabledLozenge;
