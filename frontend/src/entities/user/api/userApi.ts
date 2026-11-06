import { IUserCreatePayload } from "../model/types";
import { IUserPatchPayload } from "../model/types";
import { IUserListParams } from "../model/types";
import { buildIfMatch } from "@shared/api";
import { apiRequest } from "@shared/api";
import { HttpMethod } from "@shared/api";
import { IUser } from "../model/types";
import { IPage } from "@shared/api";
import { IUserSummary } from "../model/types";
import { UserStatus } from "../model/types";
import { UserRole } from "../model/types";
import { MAX_PAGE_SIZE } from "@shared/config";

export const fetchUserSummary = (userId: string): Promise<IUserSummary> =>
  apiRequest<IUserSummary>(`/users/${userId}/summary`);

export const fetchUserDirectory = async (
  filters: Pick<IUserListParams, "role" | "status"> = {}
): Promise<IUserSummary[]> => {
  const people: IUserSummary[] = [];
  let total = 0;

  do {
    const page = await apiRequest<IPage<IUserSummary>>("/users/directory", {
      query: { ...filters, limit: MAX_PAGE_SIZE, offset: people.length },
    });
    people.push(...page.items);
    total = page.total;
    if (page.items.length === 0) break;
  } while (people.length < total);

  return people;
};

export const fetchTechnicians = (): Promise<IUserSummary[]> =>
  fetchUserDirectory({ role: UserRole.TECHNICIAN, status: UserStatus.ACTIVE });

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
