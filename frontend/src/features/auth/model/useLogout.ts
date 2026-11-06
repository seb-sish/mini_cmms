"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { logoutRequest } from "../api/authApi";
import { useRouter } from "next/navigation";
import { ROUTES } from "@shared/config";

export const useLogout = () => {
  const router = useRouter();
  const queryClient = useQueryClient();

  const finishLogout = () => {
    queryClient.clear();
    router.replace(ROUTES.LOGIN);
  };

  return useMutation({
    mutationFn: logoutRequest,
    onSettled: finishLogout,
  });
};
