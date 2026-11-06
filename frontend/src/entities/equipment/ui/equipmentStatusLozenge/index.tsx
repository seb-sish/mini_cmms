import Lozenge from "@shared/ui/lozenge";
import { EQUIPMENT_STATUS_APPEARANCES } from "../../model/labels";
import { EQUIPMENT_STATUS_LABELS } from "../../model/labels";
import { EquipmentStatus } from "../../model/types";
import { ReactElement } from "react";

interface IEquipmentStatusLozengeProps {
  status: EquipmentStatus;
}

const EquipmentStatusLozenge = ({
  status,
}: IEquipmentStatusLozengeProps): ReactElement => {
  return (
    <Lozenge
      label={EQUIPMENT_STATUS_LABELS[status]}
      appearance={EQUIPMENT_STATUS_APPEARANCES[status]}
    />
  );
};

export default EquipmentStatusLozenge;
