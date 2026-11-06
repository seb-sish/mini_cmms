export const enum UserRole {
  ADMIN = "ADMIN",
  ENGINEER = "ENGINEER",
  TECHNICIAN = "TECHNICIAN",
  OPERATOR = "OPERATOR",
}

export const enum UserStatus {
  ACTIVE = "ACTIVE",
  BLOCKED = "BLOCKED",
}

export interface IUser {
  id: string;
  login: string;
  role: UserRole;
  status: UserStatus;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface IUserCreatePayload {
  login: string;
  password: string;
  role: UserRole;
}

export interface IUserPatchPayload {
  role?: UserRole;
  status?: UserStatus;
  new_password?: string;
}

export interface IUserListParams {
  limit: number;
  offset: number;
  q?: string;
  role?: UserRole | "";
  status?: UserStatus | "";
}

export const USER_ROLES: readonly UserRole[] = [
  UserRole.ADMIN,
  UserRole.ENGINEER,
  UserRole.TECHNICIAN,
  UserRole.OPERATOR,
];

export const USER_STATUSES: readonly UserStatus[] = [
  UserStatus.ACTIVE,
  UserStatus.BLOCKED,
];
