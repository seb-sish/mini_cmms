import { EquipmentDetailsPage } from "@pages/equipment-details";
import { ReactElement } from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Карточка оборудования",
};

interface IEquipmentDetailsPageRouteProps {
  params: Promise<{ equipmentId: string }>;
}

const EquipmentDetailsPageRoute = async ({
  params,
}: IEquipmentDetailsPageRouteProps): Promise<ReactElement> => {
  const { equipmentId } = await params;

  return <EquipmentDetailsPage equipmentId={equipmentId} />;
};

export default EquipmentDetailsPageRoute;
