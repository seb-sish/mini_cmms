import { IFaultCreatePayload } from "../model/types";
import { IFaultPatchPayload } from "../model/types";
import { IFaultListParams } from "../model/types";
import { buildIfMatch } from "@shared/api";
import { apiRequest } from "@shared/api";
import { HttpMethod } from "@shared/api";
import { IFault } from "../model/types";
import { IPage } from "@shared/api";

export const fetchFaults = (params: IFaultListParams): Promise<IPage<IFault>> =>
  apiRequest<IPage<IFault>>("/faults", { query: { ...params } });

export const fetchFault = (faultId: string): Promise<IFault> =>
  apiRequest<IFault>(`/faults/${faultId}`);

export const createFault = (payload: IFaultCreatePayload): Promise<IFault> =>
  apiRequest<IFault>("/faults", { method: HttpMethod.POST, body: payload });

export const updateFault = (
  fault: IFault,
  payload: IFaultPatchPayload
): Promise<IFault> =>
  apiRequest<IFault>(`/faults/${fault.id}`, {
    method: HttpMethod.PATCH,
    body: payload,
    ifMatch: buildIfMatch(fault.id, fault.version),
  });
