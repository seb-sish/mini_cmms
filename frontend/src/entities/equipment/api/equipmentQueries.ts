"use client";

import { keepPreviousData } from "@tanstack/react-query";
import { IEquipmentListParams } from "../model/types";
import { fetchEquipmentList } from "./equipmentApi";
import { useQuery } from "@tanstack/react-query";
import { fetchEquipment } from "./equipmentApi";
import { MAX_PAGE_SIZE } from "@shared/config";

export const equipmentKeys = {
  all: ["equipment"] as const,
  lists: () => [...equipmentKeys.all, "list"] as const,
  list: (params: IEquipmentListParams) =>
    [...equipmentKeys.lists(), params] as const,
  details: () => [...equipmentKeys.all, "detail"] as const,
  detail: (equipmentId: string) =>
    [...equipmentKeys.details(), equipmentId] as const,
  dictionaries: () => [...equipmentKeys.all, "dictionaries"] as const,
};

export const useEquipmentListQuery = (
  params: IEquipmentListParams,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: equipmentKeys.list(params),
    queryFn: () => fetchEquipmentList(params),
    placeholderData: keepPreviousData,
    enabled: isEnabled,
  });

export interface IEquipmentDictionaries {
  categories: string[];
  locations: string[];
}

const collectUnique = (values: string[]): string[] =>
  Array.from(new Set(values)).sort((left, right) =>
    left.localeCompare(right, "ru")
  );

export const useEquipmentDictionariesQuery = (isEnabled: boolean = true) =>
  useQuery({
    queryKey: equipmentKeys.dictionaries(),
    queryFn: () =>
      fetchEquipmentList({
        limit: MAX_PAGE_SIZE,
        offset: 0,
        include_archived: true,
      }),
    select: (page): IEquipmentDictionaries => ({
      categories: collectUnique(
        page.items.map((equipment) => equipment.category)
      ),
      locations: collectUnique(
        page.items.map((equipment) => equipment.location)
      ),
    }),
    staleTime: 5 * 60_000,
    enabled: isEnabled,
  });

export const useEquipmentQuery = (
  equipmentId: string,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: equipmentKeys.detail(equipmentId),
    queryFn: () => fetchEquipment(equipmentId),
    staleTime: 60_000,
    enabled: isEnabled,
  });
