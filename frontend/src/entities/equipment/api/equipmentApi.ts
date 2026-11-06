import { IEquipmentCreatePayload } from "../model/types";
import { EquipmentPatchPayload } from "../model/types";
import { IEquipmentListParams } from "../model/types";
import { IEquipment } from "../model/types";
import { buildIfMatch } from "@shared/api";
import { apiRequest } from "@shared/api";
import { HttpMethod } from "@shared/api";
import { IPage } from "@shared/api";

export const fetchEquipmentList = (
  params: IEquipmentListParams
): Promise<IPage<IEquipment>> =>
  apiRequest<IPage<IEquipment>>("/equipment", { query: { ...params } });

export const fetchEquipment = (equipmentId: string): Promise<IEquipment> =>
  apiRequest<IEquipment>(`/equipment/${equipmentId}`);

export const createEquipment = (
  payload: IEquipmentCreatePayload
): Promise<IEquipment> =>
  apiRequest<IEquipment>("/equipment", {
    method: HttpMethod.POST,
    body: payload,
  });

export const updateEquipment = (
  equipment: IEquipment,
  payload: EquipmentPatchPayload
): Promise<IEquipment> =>
  apiRequest<IEquipment>(`/equipment/${equipment.id}`, {
    method: HttpMethod.PATCH,
    body: payload,
    ifMatch: buildIfMatch(equipment.id, equipment.version),
  });

export const archiveEquipment = (equipmentId: string): Promise<IEquipment> =>
  apiRequest<IEquipment>(`/equipment/${equipmentId}/archive`, {
    method: HttpMethod.POST,
  });

export const restoreEquipment = (equipmentId: string): Promise<IEquipment> =>
  apiRequest<IEquipment>(`/equipment/${equipmentId}/restore`, {
    method: HttpMethod.POST,
  });
