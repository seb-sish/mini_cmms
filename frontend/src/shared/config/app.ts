export const APP_NAME: string = "Mini-CMMS";

export const APP_DESCRIPTION: string =
  "Планирование и контроль технического обслуживания оборудования";

export const COMPANY_TIMEZONE: string =
  process.env.NEXT_PUBLIC_COMPANY_TIMEZONE ?? "Europe/Moscow";

export const API_PROXY_PREFIX: string = "/api/v1";

export const AUTH_ROUTE_PREFIX: string = "/api/auth";

export const SESSION_COOKIE_NAME: string = "cmms_session";

export const DEFAULT_PAGE_SIZE: number = 20;

export const MAX_PAGE_SIZE: number = 100;

export const SEARCH_DEBOUNCE_MS: number = 300;
