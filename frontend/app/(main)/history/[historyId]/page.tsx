import { HistoryDetailsPage } from "@pages/history-details";
import { ReactElement } from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Запись истории",
};

interface IHistoryDetailsPageRouteProps {
  params: Promise<{ historyId: string }>;
}

const HistoryDetailsPageRoute = async ({
  params,
}: IHistoryDetailsPageRouteProps): Promise<ReactElement> => {
  const { historyId } = await params;

  return <HistoryDetailsPage historyId={historyId} />;
};

export default HistoryDetailsPageRoute;
