export interface IWorkHistory {
  id: string;
  work_order_id: string;
  equipment_id: string;
  plan_id: string | null;
  fault_id: string | null;
  technician_id: string;
  completed_at: string;
  closed_at: string;
  result: string;
  replaced_parts: string[];
  created_at: string;
}

export interface IWorkHistoryListParams {
  limit: number;
  offset: number;
  equipment_id?: string;
  technician_id?: string;
  completed_from?: string;
  completed_to?: string;
}
