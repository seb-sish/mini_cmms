"use client";

import { keepPreviousData } from "@tanstack/react-query";
import { IFaultListParams } from "../model/types";
import { useQuery } from "@tanstack/react-query";
import { fetchFaults } from "./faultApi";
import { fetchFault } from "./faultApi";

export const faultKeys = {
  all: ["faults"] as const,
  lists: () => [...faultKeys.all, "list"] as const,
  list: (params: IFaultListParams) => [...faultKeys.lists(), params] as const,
  details: () => [...faultKeys.all, "detail"] as const,
  detail: (faultId: string) => [...faultKeys.details(), faultId] as const,
};

export const useFaultsQuery = (
  params: IFaultListParams,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: faultKeys.list(params),
    queryFn: () => fetchFaults(params),
    placeholderData: keepPreviousData,
    enabled: isEnabled,
  });

export const useFaultQuery = (faultId: string, isEnabled: boolean = true) =>
  useQuery({
    queryKey: faultKeys.detail(faultId),
    queryFn: () => fetchFault(faultId),
    enabled: isEnabled,
  });
