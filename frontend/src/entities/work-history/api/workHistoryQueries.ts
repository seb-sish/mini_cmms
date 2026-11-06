"use client";

import { keepPreviousData } from "@tanstack/react-query";
import { IWorkHistoryListParams } from "../model/types";
import { fetchWorkHistoryList } from "./workHistoryApi";
import { fetchWorkHistory } from "./workHistoryApi";
import { useQuery } from "@tanstack/react-query";

export const workHistoryKeys = {
  all: ["work-history"] as const,
  lists: () => [...workHistoryKeys.all, "list"] as const,
  list: (params: IWorkHistoryListParams) =>
    [...workHistoryKeys.lists(), params] as const,
  details: () => [...workHistoryKeys.all, "detail"] as const,
  detail: (historyId: string) =>
    [...workHistoryKeys.details(), historyId] as const,
};

export const useWorkHistoryListQuery = (
  params: IWorkHistoryListParams,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: workHistoryKeys.list(params),
    queryFn: () => fetchWorkHistoryList(params),
    placeholderData: keepPreviousData,
    enabled: isEnabled,
  });

export const useWorkHistoryQuery = (historyId: string) =>
  useQuery({
    queryKey: workHistoryKeys.detail(historyId),
    queryFn: () => fetchWorkHistory(historyId),
  });
