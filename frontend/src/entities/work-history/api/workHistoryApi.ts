import { IWorkHistoryListParams } from "../model/types";
import { IWorkHistory } from "../model/types";
import { apiRequest } from "@shared/api";
import { IPage } from "@shared/api";

export const fetchWorkHistoryList = (
  params: IWorkHistoryListParams
): Promise<IPage<IWorkHistory>> =>
  apiRequest<IPage<IWorkHistory>>("/work-history", { query: { ...params } });

export const fetchWorkHistory = (historyId: string): Promise<IWorkHistory> =>
  apiRequest<IWorkHistory>(`/work-history/${historyId}`);
