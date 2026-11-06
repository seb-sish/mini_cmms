"use client";

import Link from "next/link";
import FilterBar from "@shared/ui/filterBar";
import DataTable from "@shared/ui/dataTable";
import FilterDate from "@shared/ui/filterDate";
import EmptyState from "@shared/ui/emptyState";
import Pagination from "@shared/ui/pagination";
import FilterSelect from "@shared/ui/filterSelect";
import useListParams from "@shared/lib/useListParams";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { useWorkHistoryListQuery } from "@entities/work-history";
import { IWorkHistoryListParams } from "@entities/work-history";
import { ReplacedPartsList } from "@entities/work-history";
import { IDataTableColumn } from "@shared/ui/dataTable";
import { IWorkHistory } from "@entities/work-history";
import { useTechniciansQuery } from "@entities/user";
import { EquipmentName } from "@entities/equipment";
import { buildHistoryRoute } from "@shared/config";
import { formatDateTime } from "@shared/lib/date";
import { truncateText } from "@shared/lib/text";
import { getErrorMessage } from "@shared/api";
import { IconName } from "@shared/ui/icon";
import { useViewer } from "@entities/user";
import { UserName } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";
import "./style.css";

interface IHistoryTableFilters {
  technician_id: string;
  completed_from: string;
  completed_to: string;
}

interface IHistoryTableProps {
  fixedFilters?: Pick<IWorkHistoryListParams, "equipment_id">;
  isFilterable?: boolean;
  pageSize?: number;
}

const RESULT_PREVIEW_LENGTH = 140;

const INITIAL_FILTERS: IHistoryTableFilters = {
  technician_id: "",
  completed_from: "",
  completed_to: "",
};

const HistoryTable = ({
  fixedFilters = {},
  isFilterable = true,
  pageSize,
}: IHistoryTableProps): ReactElement => {
  const viewer = useViewer();
  const isEngineer: boolean = viewer.role === UserRole.ENGINEER;
  const list = useListParams(INITIAL_FILTERS, pageSize);
  const { data: technicians } = useTechniciansQuery(isEngineer && isFilterable);
  const isRangeInvalid: boolean = Boolean(
    list.filters.completed_from &&
      list.filters.completed_to &&
      list.filters.completed_from > list.filters.completed_to
  );

  const { data, isFetching, error } = useWorkHistoryListQuery(
    {
      limit: list.limit,
      offset: list.offset,
      technician_id: list.filters.technician_id || undefined,
      completed_from: list.filters.completed_from || undefined,
      completed_to: list.filters.completed_to || undefined,
      ...fixedFilters,
    },
    !isRangeInvalid
  );

  const technicianOptions = (technicians?.items ?? []).map((technician) => ({
    value: technician.id,
    label: technician.login,
  }));

  const columns: IDataTableColumn<IWorkHistory>[] = [
    {
      key: "completed",
      title: "Выполнено",
      render: (history) => (
        <Link href={buildHistoryRoute(history.id)}>
          {formatDateTime(history.completed_at)}
        </Link>
      ),
    },
    ...(fixedFilters.equipment_id
      ? []
      : [
          {
            key: "equipment",
            title: "Оборудование",
            render: (history: IWorkHistory) => (
              <EquipmentName equipmentId={history.equipment_id} />
            ),
          },
        ]),
    {
      key: "kind",
      title: "Вид работ",
      render: (history) => (history.plan_id ? "Плановое ТО" : "Ремонт"),
    },
    {
      key: "result",
      title: "Результат",
      render: (history) => (
        <span className="history-table-result">
          {truncateText(history.result, RESULT_PREVIEW_LENGTH)}
        </span>
      ),
    },
    {
      key: "parts",
      title: "Заменённые детали",
      render: (history) => <ReplacedPartsList parts={history.replaced_parts} />,
    },
    {
      key: "technician",
      title: "Исполнитель",
      render: (history) => <UserName userId={history.technician_id} />,
    },
  ];

  return (
    <div>
      {isFilterable && (
        <FilterBar>
          {isEngineer && technicianOptions.length > 0 && (
            <FilterSelect
              label="Исполнитель"
              value={list.filters.technician_id}
              options={technicianOptions}
              onChange={(value) => list.setFilter("technician_id", value)}
            />
          )}
          <FilterDate
            label="Выполнено с"
            value={list.filters.completed_from}
            onChange={(value) => list.setFilter("completed_from", value)}
          />
          <FilterDate
            label="по"
            value={list.filters.completed_to}
            onChange={(value) => list.setFilter("completed_to", value)}
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
          title="Не удалось загрузить историю работ"
        >
          <p>{getErrorMessage(error)}</p>
        </SectionMessage>
      ) : (
        !isRangeInvalid && (
          <>
            <DataTable
              caption="История выполненных работ"
              columns={columns}
              rows={data?.items ?? []}
              getRowKey={(history) => history.id}
              isLoading={isFetching && !data}
              emptyView={
                <EmptyState
                  title="Записей истории нет"
                  description="Запись появляется после закрытия заявки главным инженером."
                  icon={IconName.HISTORY}
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
    </div>
  );
};

export default HistoryTable;
