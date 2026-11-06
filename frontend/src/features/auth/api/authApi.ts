import { AUTH_ROUTE_PREFIX } from "@shared/config";
import { httpRequest } from "@shared/api";
import { HttpMethod } from "@shared/api";
import { IUser } from "@entities/user";

export interface ILoginPayload {
  login: string;
  password: string;
}

export interface ILoginResponse {
  user: IUser;
  expires_at: string;
}

export const loginRequest = (payload: ILoginPayload): Promise<ILoginResponse> =>
  httpRequest<ILoginResponse>(`${AUTH_ROUTE_PREFIX}/login`, {
    method: HttpMethod.POST,
    body: payload,
  });

export const logoutRequest = (): Promise<void> =>
  httpRequest<void>(`${AUTH_ROUTE_PREFIX}/logout`, { method: HttpMethod.POST });
