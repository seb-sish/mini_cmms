"use client";

import Link from "next/link";
import FilterBar from "@shared/ui/filterBar";
import DataTable from "@shared/ui/dataTable";
import FilterDate from "@shared/ui/filterDate";
import EmptyState from "@shared/ui/emptyState";
import Pagination from "@shared/ui/pagination";
import SearchField from "@shared/ui/searchField";
import FilterSelect from "@shared/ui/filterSelect";
import useListParams from "@shared/lib/useListParams";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { FAULT_SEVERITY_LABELS } from "@entities/fault";
import { IDataTableColumn } from "@shared/ui/dataTable";
import { FaultSeverityLozenge } from "@entities/fault";
import { FAULT_STATUS_LABELS } from "@entities/fault";
import { FaultStatusLozenge } from "@entities/fault";
import { EquipmentName } from "@entities/equipment";
import { FAULT_SEVERITIES } from "@entities/fault";
import { IFaultListParams } from "@entities/fault";
import { buildOptions } from "@shared/lib/options";
import { buildFaultRoute } from "@shared/config";
import { FAULT_STATUSES } from "@entities/fault";
import { useFaultsQuery } from "@entities/fault";
import { FaultSeverity } from "@entities/fault";
import { truncateText } from "@shared/lib/text";
import { getErrorMessage } from "@shared/api";
import { FaultStatus } from "@entities/fault";
import { formatDate } from "@shared/lib/date";
import { IconName } from "@shared/ui/icon";
import { UserName } from "@entities/user";
import { IFault } from "@entities/fault";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

interface IFaultTableFilters {
  status: FaultStatus | "";
  severity: FaultSeverity | "";
  detected_from: string;
  detected_to: string;
}

interface IFaultTableProps {
  fixedFilters?: Pick<IFaultListParams, "equipment_id" | "author_id">;
  isFilterable?: boolean;
  pageSize?: number;
  emptyAction?: ReactNode;
}

const STATUS_OPTIONS = buildOptions(FAULT_STATUSES, FAULT_STATUS_LABELS);
const SEVERITY_OPTIONS = buildOptions(FAULT_SEVERITIES, FAULT_SEVERITY_LABELS);
const DESCRIPTION_PREVIEW_LENGTH = 120;

const INITIAL_FILTERS: IFaultTableFilters = {
  status: "",
  severity: "",
  detected_from: "",
  detected_to: "",
};

const FaultTable = ({
  fixedFilters = {},
  isFilterable = true,
  pageSize,
  emptyAction,
}: IFaultTableProps): ReactElement => {
  const list = useListParams(INITIAL_FILTERS, pageSize);
  const isRangeInvalid: boolean = Boolean(
    list.filters.detected_from &&
      list.filters.detected_to &&
      list.filters.detected_from > list.filters.detected_to
  );

  const { data, isFetching, error } = useFaultsQuery(
    {
      limit: list.limit,
      offset: list.offset,
      q: list.query,
      status: list.filters.status,
      severity: list.filters.severity,
      detected_from: list.filters.detected_from || undefined,
      detected_to: list.filters.detected_to || undefined,
      ...fixedFilters,
    },
    !isRangeInvalid
  );

  const columns: IDataTableColumn<IFault>[] = [
    {
      key: "description",
      title: "Описание",
      render: (fault) => (
        <Link
          className="fault-table-description"
          href={buildFaultRoute(fault.id)}
        >
          {truncateText(fault.description, DESCRIPTION_PREVIEW_LENGTH)}
        </Link>
      ),
    },
    ...(fixedFilters.equipment_id
      ? []
      : [
          {
            key: "equipment",
            title: "Оборудование",
            render: (fault: IFault) => (
              <EquipmentName equipmentId={fault.equipment_id} />
            ),
          },
        ]),
    {
      key: "severity",
      title: "Критичность",
      render: (fault) => <FaultSeverityLozenge severity={fault.severity} />,
    },
    {
      key: "status",
      title: "Статус",
      render: (fault) => <FaultStatusLozenge status={fault.status} />,
    },
    {
      key: "detected",
      title: "Обнаружена",
      render: (fault) => formatDate(fault.detected_on),
    },
    {
      key: "author",
      title: "Автор",
      render: (fault) => <UserName userId={fault.author_id} />,
    },
  ];

  return (
    <div>
      {isFilterable && (
        <FilterBar>
          <SearchField
            label="Поиск неисправностей"
            value={list.search}
            onChange={list.setSearch}
            placeholder="Текст описания"
          />
          <FilterSelect
            label="Статус"
            value={list.filters.status}
            options={STATUS_OPTIONS}
            onChange={(value) =>
              list.setFilter("status", value as FaultStatus | "")
            }
          />
          <FilterSelect
            label="Критичность"
            value={list.filters.severity}
            options={SEVERITY_OPTIONS}
            onChange={(value) =>
              list.setFilter("severity", value as FaultSeverity | "")
            }
          />
          <FilterDate
            label="Обнаружена с"
            value={list.filters.detected_from}
            onChange={(value) => list.setFilter("detected_from", value)}
          />
          <FilterDate
            label="по"
            value={list.filters.detected_to}
            onChange={(value) => list.setFilter("detected_to", value)}
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
          title="Не удалось загрузить неисправности"
        >
          <p>{getErrorMessage(error)}</p>
        </SectionMessage>
      ) : (
        !isRangeInvalid && (
          <>
            <DataTable
              caption="Журнал неисправностей"
              columns={columns}
              rows={data?.items ?? []}
              getRowKey={(fault) => fault.id}
              isLoading={isFetching && !data}
              emptyView={
                <EmptyState
                  title="Неисправностей не найдено"
                  icon={IconName.FAULT}
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
        )
      )}
    </div>
  );
};

export default FaultTable;
