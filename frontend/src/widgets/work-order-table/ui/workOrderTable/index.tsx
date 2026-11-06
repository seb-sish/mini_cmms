"use client";

import Link from "next/link";
import FilterBar from "@shared/ui/filterBar";
import DataTable from "@shared/ui/dataTable";
import EmptyState from "@shared/ui/emptyState";
import Pagination from "@shared/ui/pagination";
import SearchField from "@shared/ui/searchField";
import FilterSelect from "@shared/ui/filterSelect";
import useListParams from "@shared/lib/useListParams";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { WORK_ORDER_PRIORITY_LABELS } from "@entities/work-order";
import { WORK_ORDER_STATUS_LABELS } from "@entities/work-order";
import { WORK_ORDER_TYPE_LABELS } from "@entities/work-order";
import { WorkOrderStatusLozenge } from "@entities/work-order";
import { WorkOrderPriorityLabel } from "@entities/work-order";
import { WORK_ORDER_PRIORITIES } from "@entities/work-order";
import { IWorkOrderListParams } from "@entities/work-order";
import { WORK_ORDER_STATUSES } from "@entities/work-order";
import { useWorkOrdersQuery } from "@entities/work-order";
import { WorkOrderPriority } from "@entities/work-order";
import { IDataTableColumn } from "@shared/ui/dataTable";
import { WORK_ORDER_TYPES } from "@entities/work-order";
import { WorkOrderStatus } from "@entities/work-order";
import { buildWorkOrderRoute } from "@shared/config";
import { useTechniciansQuery } from "@entities/user";
import { WorkOrderSort } from "@entities/work-order";
import { WorkOrderType } from "@entities/work-order";
import { EquipmentName } from "@entities/equipment";
import { buildOptions } from "@shared/lib/options";
import { formatDateTime } from "@shared/lib/date";
import { IWorkOrder } from "@entities/work-order";
import { getErrorMessage } from "@shared/api";
import { IconName } from "@shared/ui/icon";
import { useViewer } from "@entities/user";
import { UserName } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

type WorkOrderFixedFilters = Pick<
  IWorkOrderListParams,
  "equipment_id" | "fault_id" | "schedule_id" | "assignee_id" | "status"
>;

interface IWorkOrderTableFilters {
  status: WorkOrderStatus | "";
  priority: WorkOrderPriority | "";
  type: WorkOrderType | "";
  assignee_id: string;
  sort: WorkOrderSort;
}

interface IWorkOrderTableProps {
  fixedFilters?: WorkOrderFixedFilters;
  isFilterable?: boolean;
  pageSize?: number;
  emptyTitle?: string;
  emptyAction?: ReactNode;
}

const STATUS_OPTIONS = buildOptions(
  WORK_ORDER_STATUSES,
  WORK_ORDER_STATUS_LABELS
);
const PRIORITY_OPTIONS = buildOptions(
  WORK_ORDER_PRIORITIES,
  WORK_ORDER_PRIORITY_LABELS
);
const TYPE_OPTIONS = buildOptions(WORK_ORDER_TYPES, WORK_ORDER_TYPE_LABELS);

const INITIAL_FILTERS: IWorkOrderTableFilters = {
  status: "",
  priority: "",
  type: "",
  assignee_id: "",
  sort: WorkOrderSort.CREATED_DESC,
};

const DEFAULT_EMPTY_TITLE: string = "Заявок не найдено";

const WorkOrderTable = ({
  fixedFilters = {},
  isFilterable = true,
  pageSize,
  emptyTitle = DEFAULT_EMPTY_TITLE,
  emptyAction,
}: IWorkOrderTableProps): ReactElement => {
  const viewer = useViewer();
  const list = useListParams(INITIAL_FILTERS, pageSize);
  const isEngineer: boolean = viewer.role === UserRole.ENGINEER;
  const { data: technicians } = useTechniciansQuery(isEngineer && isFilterable);

  const { data, isFetching, error } = useWorkOrdersQuery({
    limit: list.limit,
    offset: list.offset,
    q: list.query,
    status: list.filters.status,
    priority: list.filters.priority,
    type: list.filters.type,
    assignee_id: list.filters.assignee_id || undefined,
    sort: list.filters.sort,
    ...fixedFilters,
  });

  const technicianOptions = (technicians?.items ?? []).map((technician) => ({
    value: technician.id,
    label: technician.login,
  }));

  const columns: IDataTableColumn<IWorkOrder>[] = [
    {
      key: "number",
      title: "Заявка",
      render: (workOrder) => (
        <div className="work-order-table-title">
          <Link href={buildWorkOrderRoute(workOrder.id)} className="code-text">
            {workOrder.number}
          </Link>
          <span>{workOrder.title}</span>
        </div>
      ),
    },
    {
      key: "type",
      title: "Тип",
      render: (workOrder) => WORK_ORDER_TYPE_LABELS[workOrder.type],
    },
    {
      key: "status",
      title: "Статус",
      sortKey: WorkOrderSort.STATUS_ASC,
      render: (workOrder) => (
        <WorkOrderStatusLozenge status={workOrder.status} />
      ),
    },
    {
      key: "priority",
      title: "Приоритет",
      render: (workOrder) => (
        <WorkOrderPriorityLabel priority={workOrder.priority} />
      ),
    },
    ...(fixedFilters.equipment_id
      ? []
      : [
          {
            key: "equipment",
            title: "Оборудование",
            render: (workOrder: IWorkOrder) => (
              <EquipmentName equipmentId={workOrder.equipment_id} />
            ),
          },
        ]),
    {
      key: "assignee",
      title: "Исполнитель",
      render: (workOrder) => <UserName userId={workOrder.assignee_id} />,
    },
    {
      key: "created",
      title: "Создана",
      sortKey: WorkOrderSort.CREATED_ASC,
      render: (workOrder) => (
        <span className="body-small text-subtle">
          {formatDateTime(workOrder.created_at)}
        </span>
      ),
    },
  ];

  const handleSortChange = (sortValue: string) => {
    list.setFilter("sort", sortValue as WorkOrderSort);
  };

  return (
    <div className="work-order-table">
      {isFilterable && (
        <FilterBar>
          <SearchField
            label="Поиск заявок"
            value={list.search}
            onChange={list.setSearch}
            placeholder="Номер, заголовок, описание"
          />
          <FilterSelect
            label="Статус"
            value={list.filters.status}
            options={STATUS_OPTIONS}
            onChange={(value) =>
              list.setFilter("status", value as WorkOrderStatus | "")
            }
          />
          <FilterSelect
            label="Приоритет"
            value={list.filters.priority}
            options={PRIORITY_OPTIONS}
            onChange={(value) =>
              list.setFilter("priority", value as WorkOrderPriority | "")
            }
          />
          <FilterSelect
            label="Тип"
            value={list.filters.type}
            options={TYPE_OPTIONS}
            onChange={(value) =>
              list.setFilter("type", value as WorkOrderType | "")
            }
          />
          {isEngineer &&
            technicianOptions.length > 0 &&
            !fixedFilters.assignee_id && (
              <FilterSelect
                label="Исполнитель"
                value={list.filters.assignee_id}
                options={technicianOptions}
                onChange={(value) => list.setFilter("assignee_id", value)}
              />
            )}
        </FilterBar>
      )}
      {error ? (
        <SectionMessage
          appearance={SectionMessageAppearance.ERROR}
          title="Не удалось загрузить заявки"
        >
          <p>{getErrorMessage(error)}</p>
        </SectionMessage>
      ) : (
        <>
          <DataTable
            caption="Заявки на обслуживание"
            columns={columns}
            rows={data?.items ?? []}
            getRowKey={(workOrder) => workOrder.id}
            isLoading={isFetching && !data}
            sortValue={isFilterable ? list.filters.sort : undefined}
            onSortChange={isFilterable ? handleSortChange : undefined}
            emptyView={
              <EmptyState
                title={emptyTitle}
                icon={IconName.WORK_ORDER}
                action={emptyAction}
              />
            }
          />
          {data && (
            <Pagination
              total={data.total}
              limit={list.limit}
              offset={list.offset}
              onChange={list.setOffset}
            />
          )}
        </>
      )}
    </div>
  );
};

export default WorkOrderTable;
