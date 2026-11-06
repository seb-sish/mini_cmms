export const enum NotificationType {
  THREE_DAYS_BEFORE = "THREE_DAYS_BEFORE",
  ON_DUE_DATE = "ON_DUE_DATE",
}

export interface INotification {
  id: string;
  recipient_id: string;
  plan_id: string;
  schedule_id: string;
  equipment_id: string;
  planned_due_on: string;
  type: NotificationType;
  message: string;
  created_at: string;
}

export interface INotificationListParams {
  limit: number;
  offset: number;
  type?: NotificationType | "";
  planned_due_on?: string;
}

export const NOTIFICATION_TYPES: readonly NotificationType[] = [
  NotificationType.THREE_DAYS_BEFORE,
  NotificationType.ON_DUE_DATE,
];
