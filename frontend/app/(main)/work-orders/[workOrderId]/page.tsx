import { WorkOrderDetailsPage } from "@pages/work-order-details";
import { ReactElement } from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Заявка",
};

interface IWorkOrderDetailsPageRouteProps {
  params: Promise<{ workOrderId: string }>;
}

const WorkOrderDetailsPageRoute = async ({
  params,
}: IWorkOrderDetailsPageRouteProps): Promise<ReactElement> => {
  const { workOrderId } = await params;

  return <WorkOrderDetailsPage workOrderId={workOrderId} />;
};

export default WorkOrderDetailsPageRoute;
