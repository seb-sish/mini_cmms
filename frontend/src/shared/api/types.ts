export interface IPage<TItem> {
  items: TItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface IPaginationParams {
  limit: number;
  offset: number;
}

export interface IVersionedEntity {
  id: string;
  version: number;
}
