import { QueryClient } from "@tanstack/react-query";
import { isApiError } from "@shared/api";

const MAX_QUERY_RETRIES = 2;
const SERVER_ERROR_STATUS = 500;

export const shouldRetryQuery = (
  failureCount: number,
  error: unknown
): boolean => {
  if (failureCount >= MAX_QUERY_RETRIES) return false;

  if (!isApiError(error)) return true;

  return error.status === 0 || error.status >= SERVER_ERROR_STATUS;
};

export const createQueryClient = (): QueryClient =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: shouldRetryQuery,
        staleTime: 30_000,
      },
      mutations: {
        retry: false,
      },
    },
  });
