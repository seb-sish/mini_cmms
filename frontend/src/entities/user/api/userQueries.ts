"use client";

import { keepPreviousData } from "@tanstack/react-query";
import { IUserListParams } from "../model/types";
import { useQuery } from "@tanstack/react-query";
import { MAX_PAGE_SIZE } from "@shared/config";
import { fetchCurrentUser } from "./userApi";
import { UserStatus } from "../model/types";
import { UserRole } from "../model/types";
import { fetchUsers } from "./userApi";
import { fetchUser } from "./userApi";

export const userKeys = {
  all: ["users"] as const,
  viewer: () => [...userKeys.all, "viewer"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (params: IUserListParams) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, "detail"] as const,
  detail: (userId: string) => [...userKeys.details(), userId] as const,
  technicians: () => [...userKeys.all, "technicians"] as const,
};

export const useViewerQuery = () =>
  useQuery({
    queryKey: userKeys.viewer(),
    queryFn: fetchCurrentUser,
    staleTime: 60_000,
    retry: false,
  });

export const useUsersQuery = (params: IUserListParams) =>
  useQuery({
    queryKey: userKeys.list(params),
    queryFn: () => fetchUsers(params),
    placeholderData: keepPreviousData,
  });

export const useUserQuery = (userId: string) =>
  useQuery({
    queryKey: userKeys.detail(userId),
    queryFn: () => fetchUser(userId),
  });

export const useTechniciansQuery = (isEnabled: boolean) =>
  useQuery({
    queryKey: userKeys.technicians(),
    queryFn: () =>
      fetchUsers({
        limit: MAX_PAGE_SIZE,
        offset: 0,
        role: UserRole.TECHNICIAN,
        status: UserStatus.ACTIVE,
      }),
    enabled: isEnabled,
    staleTime: 5 * 60_000,
    retry: false,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
  });
