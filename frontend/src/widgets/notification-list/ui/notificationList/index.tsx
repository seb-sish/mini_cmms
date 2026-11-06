"use client";

import FilterBar from "@shared/ui/filterBar";
import DataTable from "@shared/ui/dataTable";
import EmptyState from "@shared/ui/emptyState";
import Pagination from "@shared/ui/pagination";
import FilterSelect from "@shared/ui/filterSelect";
import useListParams from "@shared/lib/useListParams";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { NOTIFICATION_TYPE_LABELS } from "@entities/notification";
import { NotificationTypeLozenge } from "@entities/notification";
import { useNotificationsQuery } from "@entities/notification";
import { NOTIFICATION_TYPES } from "@entities/notification";
import { NotificationType } from "@entities/notification";
import { IDataTableColumn } from "@shared/ui/dataTable";
import { INotification } from "@entities/notification";
import { PlanName } from "@entities/maintenance-plan";
import { EquipmentName } from "@entities/equipment";
import { buildOptions } from "@shared/lib/options";
import { formatDateTime } from "@shared/lib/date";
import { getErrorMessage } from "@shared/api";
import { formatDate } from "@shared/lib/date";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";

interface INotificationListFilters {
  type: NotificationType | "";
}

interface INotificationListProps {
  isFilterable?: boolean;
  pageSize?: number;
}

const TYPE_OPTIONS = buildOptions(NOTIFICATION_TYPES, NOTIFICATION_TYPE_LABELS);
const INITIAL_FILTERS: INotificationListFilters = { type: "" };

const NotificationList = ({
  isFilterable = true,
  pageSize,
}: INotificationListProps): ReactElement => {
  const list = useListParams(INITIAL_FILTERS, pageSize);

  const { data, isFetching, error } = useNotificationsQuery({
    limit: list.limit,
    offset: list.offset,
    type: list.filters.type,
  });

  const columns: IDataTableColumn<INotification>[] = [
    {
      key: "type",
      title: "Тип",
      render: (notification) => (
        <NotificationTypeLozenge type={notification.type} />
      ),
    },
    {
      key: "message",
      title: "Сообщение",
      render: (notification) => notification.message,
    },
    {
      key: "due",
      title: "Срок ТО",
      render: (notification) => (
        <strong>{formatDate(notification.planned_due_on)}</strong>
      ),
    },
    {
      key: "equipment",
      title: "Оборудование",
      render: (notification) => (
        <EquipmentName equipmentId={notification.equipment_id} />
      ),
    },
    {
      key: "plan",
      title: "Регламент",
      render: (notification) => <PlanName planId={notification.plan_id} />,
    },
    {
      key: "created",
      title: "Создано",
      render: (notification) => (
        <span className="body-small text-subtle">
          {formatDateTime(notification.created_at)}
        </span>
      ),
    },
  ];

  return (
    <div>
      {isFilterable && (
        <FilterBar>
          <FilterSelect
            label="Тип напоминания"
            value={list.filters.type}
            options={TYPE_OPTIONS}
            onChange={(value) =>
              list.setFilter("type", value as NotificationType | "")
            }
          />
        </FilterBar>
      )}
      {error ? (
        <SectionMessage
          appearance={SectionMessageAppearance.ERROR}
          title="Не удалось загрузить уведомления"
        >
          <p>{getErrorMessage(error)}</p>
        </SectionMessage>
      ) : (
        <>
          <DataTable
            caption="Напоминания о техническом обслуживании"
            columns={columns}
            rows={data?.items ?? []}
            getRowKey={(notification) => notification.id}
            isLoading={isFetching && !data}
            emptyView={
              <EmptyState
                title="Напоминаний нет"
                description="Напоминания формируются автоматически за 3 дня до срока ТО и в день ТО."
                icon={IconName.BELL}
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

export default NotificationList;
