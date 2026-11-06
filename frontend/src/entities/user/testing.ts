import { UserStatus } from "./model/types";
import { UserRole } from "./model/types";
import { IUser } from "./model/types";

export const buildUserFixture = (overrides: Partial<IUser> = {}): IUser => ({
  id: "user-1",
  login: "user",
  role: UserRole.ENGINEER,
  status: UserStatus.ACTIVE,
  version: 1,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
  ...overrides,
});
