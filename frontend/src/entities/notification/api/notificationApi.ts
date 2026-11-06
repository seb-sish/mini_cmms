import { INotificationListParams } from "../model/types";
import { INotification } from "../model/types";
import { apiRequest } from "@shared/api";
import { IPage } from "@shared/api";

export const fetchNotifications = (
  params: INotificationListParams
): Promise<IPage<INotification>> =>
  apiRequest<IPage<INotification>>("/notifications", { query: { ...params } });
