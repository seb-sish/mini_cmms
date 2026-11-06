"use client";

import Link from "next/link";
import { useEquipmentQuery } from "../../api/equipmentQueries";
import { buildEquipmentRoute } from "@shared/config";
import { shortenId } from "@shared/lib/options";
import { ReactElement } from "react";
import "./style.css";

interface IEquipmentNameProps {
  equipmentId: string;
  isLink?: boolean;
}

const EquipmentName = ({
  equipmentId,
  isLink = true,
}: IEquipmentNameProps): ReactElement => {
  const { data: equipment, isError } = useEquipmentQuery(equipmentId);

  if (isError) {
    return (
      <span className="text-subtlest" title={equipmentId}>
        Оборудование {shortenId(equipmentId)}
      </span>
    );
  }

  if (!equipment) return <span className="text-subtlest">Загрузка...</span>;

  const content = (
    <>
      <span>{equipment.name}</span>
      <span className="equipment-name-number code-text">
        {equipment.inventory_number}
      </span>
    </>
  );

  if (!isLink) return <span className="equipment-name">{content}</span>;

  return (
    <Link className="equipment-name" href={buildEquipmentRoute(equipmentId)}>
      {content}
    </Link>
  );
};

export default EquipmentName;
