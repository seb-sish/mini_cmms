import { FaultDetailsPage } from "@pages/fault-details";
import { ReactElement } from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Неисправность",
};

interface IFaultDetailsPageRouteProps {
  params: Promise<{ faultId: string }>;
}

const FaultDetailsPageRoute = async ({
  params,
}: IFaultDetailsPageRouteProps): Promise<ReactElement> => {
  const { faultId } = await params;

  return <FaultDetailsPage faultId={faultId} />;
};

export default FaultDetailsPageRoute;
