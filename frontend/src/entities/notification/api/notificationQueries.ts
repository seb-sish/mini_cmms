"use client";

import { INotificationListParams } from "../model/types";
import { keepPreviousData } from "@tanstack/react-query";
import { fetchNotifications } from "./notificationApi";
import { useQuery } from "@tanstack/react-query";

const NOTIFICATIONS_REFRESH_MS = 5 * 60_000;

export const notificationKeys = {
  all: ["notifications"] as const,
  lists: () => [...notificationKeys.all, "list"] as const,
  list: (params: INotificationListParams) =>
    [...notificationKeys.lists(), params] as const,
};

export const useNotificationsQuery = (
  params: INotificationListParams,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: notificationKeys.list(params),
    queryFn: () => fetchNotifications(params),
    placeholderData: keepPreviousData,
    refetchInterval: NOTIFICATIONS_REFRESH_MS,
    enabled: isEnabled,
  });
