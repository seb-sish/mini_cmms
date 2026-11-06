"use client";

import { keepPreviousData } from "@tanstack/react-query";
import { fetchWorkOrderEvents } from "./workOrderApi";
import { IWorkOrderListParams } from "../model/types";
import { useQuery } from "@tanstack/react-query";
import { fetchWorkOrders } from "./workOrderApi";
import { fetchWorkOrder } from "./workOrderApi";
import { MAX_PAGE_SIZE } from "@shared/config";

export const workOrderKeys = {
  all: ["work-orders"] as const,
  lists: () => [...workOrderKeys.all, "list"] as const,
  list: (params: IWorkOrderListParams) =>
    [...workOrderKeys.lists(), params] as const,
  details: () => [...workOrderKeys.all, "detail"] as const,
  detail: (workOrderId: string) =>
    [...workOrderKeys.details(), workOrderId] as const,
  events: (workOrderId: string) =>
    [...workOrderKeys.detail(workOrderId), "events"] as const,
};

export const useWorkOrdersQuery = (
  params: IWorkOrderListParams,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: workOrderKeys.list(params),
    queryFn: () => fetchWorkOrders(params),
    placeholderData: keepPreviousData,
    enabled: isEnabled,
  });

export const useWorkOrderQuery = (workOrderId: string) =>
  useQuery({
    queryKey: workOrderKeys.detail(workOrderId),
    queryFn: () => fetchWorkOrder(workOrderId),
  });

export const useWorkOrderEventsQuery = (workOrderId: string) =>
  useQuery({
    queryKey: workOrderKeys.events(workOrderId),
    queryFn: () => fetchWorkOrderEvents(workOrderId, MAX_PAGE_SIZE, 0),
  });
