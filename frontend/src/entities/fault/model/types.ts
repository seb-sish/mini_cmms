export const enum FaultSeverity {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL",
}

export const enum FaultStatus {
  OPEN = "OPEN",
  IN_PROGRESS = "IN_PROGRESS",
  RESOLVED = "RESOLVED",
}

export interface IFault {
  id: string;
  equipment_id: string;
  description: string;
  detected_on: string;
  severity: FaultSeverity;
  status: FaultStatus;
  author_id: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface IFaultCreatePayload {
  equipment_id: string;
  description: string;
  detected_on: string;
  severity: FaultSeverity;
}

export interface IFaultPatchPayload {
  description?: string;
  severity?: FaultSeverity;
  detected_on?: string;
}

export interface IFaultListParams {
  limit: number;
  offset: number;
  q?: string;
  equipment_id?: string;
  status?: FaultStatus | "";
  severity?: FaultSeverity | "";
  author_id?: string;
  detected_from?: string;
  detected_to?: string;
}

export const FAULT_SEVERITIES: readonly FaultSeverity[] = [
  FaultSeverity.LOW,
  FaultSeverity.MEDIUM,
  FaultSeverity.HIGH,
  FaultSeverity.CRITICAL,
];

export const FAULT_STATUSES: readonly FaultStatus[] = [
  FaultStatus.OPEN,
  FaultStatus.IN_PROGRESS,
  FaultStatus.RESOLVED,
];

export const FAULT_LIMITS = {
  DESCRIPTION_MIN: 5,
  DESCRIPTION_MAX: 2000,
} as const;
