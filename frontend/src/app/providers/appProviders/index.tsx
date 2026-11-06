"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { setUnauthorizedHandler } from "@shared/api";
import { createQueryClient } from "../queryClient";
import { buildLoginRoute } from "@shared/config";
import { FlagsProvider } from "@shared/ui/flag";
import { useRouter } from "next/navigation";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";
import { ReactNode } from "react";
import { useEffect } from "react";
import { useState } from "react";

interface IAppProvidersProps {
  children: ReactNode;
}

const AppProviders = ({ children }: IAppProvidersProps): ReactElement => {
  const router = useRouter();
  const [queryClient] = useState(createQueryClient);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      const currentPath = window.location.pathname;

      if (currentPath === ROUTES.LOGIN) return;

      queryClient.clear();
      router.replace(
        buildLoginRoute(`${currentPath}${window.location.search}`)
      );
    });

    return () => setUnauthorizedHandler(null);
  }, [queryClient, router]);

  return (
    <QueryClientProvider client={queryClient}>
      <FlagsProvider>{children}</FlagsProvider>
    </QueryClientProvider>
  );
};

export default AppProviders;
