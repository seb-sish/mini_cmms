import { IUserCreatePayload } from "../model/types";
import { IUserPatchPayload } from "../model/types";
import { IUserListParams } from "../model/types";
import { buildIfMatch } from "@shared/api";
import { apiRequest } from "@shared/api";
import { HttpMethod } from "@shared/api";
import { IUser } from "../model/types";
import { IPage } from "@shared/api";

export const fetchCurrentUser = (): Promise<IUser> =>
  apiRequest<IUser>("/auth/me");

export const fetchUsers = (params: IUserListParams): Promise<IPage<IUser>> =>
  apiRequest<IPage<IUser>>("/users", { query: { ...params } });

export const fetchUser = (userId: string): Promise<IUser> =>
  apiRequest<IUser>(`/users/${userId}`);

export const createUser = (payload: IUserCreatePayload): Promise<IUser> =>
  apiRequest<IUser>("/users", { method: HttpMethod.POST, body: payload });

export const updateUser = (
  user: IUser,
  payload: IUserPatchPayload
): Promise<IUser> =>
  apiRequest<IUser>(`/users/${user.id}`, {
    method: HttpMethod.PATCH,
    body: payload,
    ifMatch: buildIfMatch(user.id, user.version),
  });
