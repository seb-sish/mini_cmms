export interface IMaintenanceSchedule {
  id: string;
  plan_id: string;
  equipment_id: string;
  last_completed_on: string | null;
  next_due_on: string;
  is_overdue: boolean;
  has_current_work_order: boolean;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface IMaintenanceScheduleListParams {
  limit: number;
  offset: number;
  plan_id?: string;
  equipment_id?: string;
  is_active?: boolean;
  due_from?: string;
  due_to?: string;
  overdue?: boolean;
}
