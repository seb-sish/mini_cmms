"use client";

import Button from "@shared/ui/button";
import Lozenge from "@shared/ui/lozenge";
import FilterBar from "@shared/ui/filterBar";
import DataTable from "@shared/ui/dataTable";
import FilterDate from "@shared/ui/filterDate";
import EmptyState from "@shared/ui/emptyState";
import Pagination from "@shared/ui/pagination";
import FilterSelect from "@shared/ui/filterSelect";
import useListParams from "@shared/lib/useListParams";
import SectionMessage from "@shared/ui/sectionMessage";
import { IMaintenanceScheduleListParams } from "@entities/maintenance-schedule";
import { useMaintenanceSchedulesQuery } from "@entities/maintenance-schedule";
import { IMaintenanceSchedule } from "@entities/maintenance-schedule";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { ScheduleDueLozenge } from "@entities/maintenance-schedule";
import { CreateWorkOrderModal } from "@features/work-order-create";
import { IDataTableColumn } from "@shared/ui/dataTable";
import { LozengeAppearance } from "@shared/ui/lozenge";
import { useViewerPermissions } from "@entities/user";
import { PlanName } from "@entities/maintenance-plan";
import { buildWorkOrderRoute } from "@shared/config";
import { WorkOrderType } from "@entities/work-order";
import { EquipmentName } from "@entities/equipment";
import { ISelectOption } from "@shared/lib/options";
import { getCompanyToday } from "@shared/lib/date";
import { ButtonSpacing } from "@shared/ui/button";
import { IWorkOrder } from "@entities/work-order";
import { getErrorMessage } from "@shared/api";
import { formatDate } from "@shared/lib/date";
import { useRouter } from "next/navigation";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import { useState } from "react";
import "./style.css";

const enum ActivityFilter {
  ACTIVE = "",
  INACTIVE = "inactive",
  ALL = "all",
}

const enum OverdueFilter {
  ANY = "",
  OVERDUE = "overdue",
  NOT_OVERDUE = "not-overdue",
}

interface IScheduleTableFilters {
  activity: ActivityFilter;
  overdue: OverdueFilter;
  due_from: string;
  due_to: string;
}

interface IScheduleTableProps {
  fixedFilters?: Pick<
    IMaintenanceScheduleListParams,
    "plan_id" | "equipment_id"
  >;
  initialOverdue?: boolean;
  isFilterable?: boolean;
  pageSize?: number;
}

const ACTIVITY_OPTIONS: ISelectOption[] = [
  { value: ActivityFilter.INACTIVE, label: "Неактивные" },
  { value: ActivityFilter.ALL, label: "Все" },
];

const OVERDUE_OPTIONS: ISelectOption[] = [
  { value: OverdueFilter.OVERDUE, label: "Просроченные" },
  { value: OverdueFilter.NOT_OVERDUE, label: "В срок" },
];

const toActiveParam = (activity: ActivityFilter): boolean | undefined => {
  if (activity === ActivityFilter.ALL) return undefined;

  return activity === ActivityFilter.ACTIVE;
};

const toOverdueParam = (overdue: OverdueFilter): boolean | undefined => {
  if (overdue === OverdueFilter.ANY) return undefined;

  return overdue === OverdueFilter.OVERDUE;
};

const ScheduleTable = ({
  fixedFilters = {},
  initialOverdue = false,
  isFilterable = true,
  pageSize,
}: IScheduleTableProps): ReactElement => {
  const router = useRouter();
  const permissions = useViewerPermissions();
  const today: string = getCompanyToday();
  const [scheduleForWorkOrder, setScheduleForWorkOrder] =
    useState<IMaintenanceSchedule | null>(null);
  const list = useListParams<IScheduleTableFilters>(
    {
      activity: ActivityFilter.ACTIVE,
      overdue: initialOverdue ? OverdueFilter.OVERDUE : OverdueFilter.ANY,
      due_from: "",
      due_to: "",
    },
    pageSize
  );
  const isRangeInvalid: boolean = Boolean(
    list.filters.due_from &&
      list.filters.due_to &&
      list.filters.due_from > list.filters.due_to
  );

  const { data, isFetching, error } = useMaintenanceSchedulesQuery(
    {
      limit: list.limit,
      offset: list.offset,
      is_active: toActiveParam(list.filters.activity),
      overdue: toOverdueParam(list.filters.overdue),
      due_from: list.filters.due_from || undefined,
      due_to: list.filters.due_to || undefined,
      ...fixedFilters,
    },
    !isRangeInvalid
  );

  const closeCreateModal = () => {
    setScheduleForWorkOrder(null);
  };

  const handleWorkOrderCreated = (workOrder: IWorkOrder) => {
    router.push(buildWorkOrderRoute(workOrder.id));
  };

  const columns: IDataTableColumn<IMaintenanceSchedule>[] = [
    {
      key: "due",
      title: "Срок ТО",
      render: (schedule) => (
        <div className="schedule-table-due">
          <strong>{formatDate(schedule.next_due_on)}</strong>
          <ScheduleDueLozenge schedule={schedule} today={today} />
        </div>
      ),
    },
    ...(fixedFilters.equipment_id
      ? []
      : [
          {
            key: "equipment",
            title: "Оборудование",
            render: (schedule: IMaintenanceSchedule) => (
              <EquipmentName equipmentId={schedule.equipment_id} />
            ),
          },
        ]),
    ...(fixedFilters.plan_id
      ? []
      : [
          {
            key: "plan",
            title: "Регламент",
            render: (schedule: IMaintenanceSchedule) => (
              <PlanName planId={schedule.plan_id} />
            ),
          },
        ]),
    {
      key: "last",
      title: "Последнее ТО",
      render: (schedule) =>
        schedule.last_completed_on ? (
          formatDate(schedule.last_completed_on)
        ) : (
          <span className="text-subtlest">Не проводилось</span>
        ),
    },
    {
      key: "work-order",
      title: "Заявка",
      render: (schedule) => {
        if (schedule.has_current_work_order) {
          return (
            <Lozenge
              label="Заявка создана"
              appearance={LozengeAppearance.IN_PROGRESS}
            />
          );
        }

        if (!permissions.canCreatePlannedWorkOrder || !schedule.active) {
          return <span className="text-subtlest">Нет</span>;
        }

        const handleCreate = () => {
          setScheduleForWorkOrder(schedule);
        };

        return (
          <Button
            label="Создать заявку"
            spacing={ButtonSpacing.COMPACT}
            iconBefore={IconName.ADD}
            onClick={handleCreate}
          />
        );
      },
    },
  ];

  return (
    <div>
      {isFilterable && (
        <FilterBar>
          <FilterSelect
            label="Просрочка"
            value={list.filters.overdue}
            options={OVERDUE_OPTIONS}
            onChange={(value) =>
              list.setFilter("overdue", value as OverdueFilter)
            }
          />
          <FilterSelect
            label="Состояние"
            value={list.filters.activity}
            options={ACTIVITY_OPTIONS}
            allLabel="Активные"
            onChange={(value) =>
              list.setFilter("activity", value as ActivityFilter)
            }
          />
          <FilterDate
            label="Срок с"
            value={list.filters.due_from}
            onChange={(value) => list.setFilter("due_from", value)}
          />
          <FilterDate
            label="по"
            value={list.filters.due_to}
            onChange={(value) => list.setFilter("due_to", value)}
          />
        </FilterBar>
      )}
      {isRangeInvalid && (
        <SectionMessage appearance={SectionMessageAppearance.WARNING}>
          <p>Дата начала периода позже даты окончания.</p>
        </SectionMessage>
      )}
      {error ? (
        <SectionMessage
          appearance={SectionMessageAppearance.ERROR}
          title="Не удалось загрузить график ТО"
        >
          <p>{getErrorMessage(error)}</p>
        </SectionMessage>
      ) : (
        !isRangeInvalid && (
          <>
            <DataTable
              caption="График технического обслуживания"
              columns={columns}
              rows={data?.items ?? []}
              getRowKey={(schedule) => schedule.id}
              isLoading={isFetching && !data}
              emptyView={
                <EmptyState
                  title="Сроков ТО не найдено"
                  description="Графики появляются после создания регламентов ТО."
                  icon={IconName.CALENDAR}
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
        )
      )}
      {scheduleForWorkOrder && (
        <CreateWorkOrderModal
          initial={{
            type: WorkOrderType.PLANNED,
            equipmentId: scheduleForWorkOrder.equipment_id,
            scheduleId: scheduleForWorkOrder.id,
          }}
          onClose={closeCreateModal}
          onCreated={handleWorkOrderCreated}
        />
      )}
    </div>
  );
};

export default ScheduleTable;
