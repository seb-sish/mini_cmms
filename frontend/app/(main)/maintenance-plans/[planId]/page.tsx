import { PlanDetailsPage } from "@pages/plan-details";
import { ReactElement } from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Регламент ТО",
};

interface IPlanDetailsPageRouteProps {
  params: Promise<{ planId: string }>;
}

const PlanDetailsPageRoute = async ({
  params,
}: IPlanDetailsPageRouteProps): Promise<ReactElement> => {
  const { planId } = await params;

  return <PlanDetailsPage planId={planId} />;
};

export default PlanDetailsPageRoute;
