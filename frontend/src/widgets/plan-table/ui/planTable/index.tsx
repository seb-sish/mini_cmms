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
import { useMaintenancePlansQuery } from "@entities/maintenance-plan";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { PlanEnabledLozenge } from "@entities/maintenance-plan";
import { PLAN_SCOPE_LABELS } from "@entities/maintenance-plan";
import { IMaintenancePlan } from "@entities/maintenance-plan";
import { formatInterval } from "@entities/maintenance-plan";
import { buildMaintenancePlanRoute } from "@shared/config";
import { PLAN_SCOPES } from "@entities/maintenance-plan";
import { IDataTableColumn } from "@shared/ui/dataTable";
import { PlanScope } from "@entities/maintenance-plan";
import { EquipmentName } from "@entities/equipment";
import { ISelectOption } from "@shared/lib/options";
import { buildOptions } from "@shared/lib/options";
import { getErrorMessage } from "@shared/api";
import { formatDate } from "@shared/lib/date";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import { ReactNode } from "react";

const enum EnabledFilter {
  ANY = "",
  ENABLED = "enabled",
  PAUSED = "paused",
}

interface IPlanTableFilters {
  scope: PlanScope | "";
  enabled: EnabledFilter;
}

interface IPlanTableProps {
  emptyAction?: ReactNode;
}

const SCOPE_OPTIONS = buildOptions(PLAN_SCOPES, PLAN_SCOPE_LABELS);

const ENABLED_OPTIONS: ISelectOption[] = [
  { value: EnabledFilter.ENABLED, label: "Включённые" },
  { value: EnabledFilter.PAUSED, label: "На паузе" },
];

const INITIAL_FILTERS: IPlanTableFilters = {
  scope: "",
  enabled: EnabledFilter.ANY,
};

const PlanTable = ({ emptyAction }: IPlanTableProps): ReactElement => {
  const list = useListParams(INITIAL_FILTERS);

  const { data, isFetching, error } = useMaintenancePlansQuery({
    limit: list.limit,
    offset: list.offset,
    q: list.query,
    scope: list.filters.scope,
    enabled:
      list.filters.enabled === EnabledFilter.ANY
        ? undefined
        : list.filters.enabled === EnabledFilter.ENABLED,
  });

  const columns: IDataTableColumn<IMaintenancePlan>[] = [
    {
      key: "name",
      title: "Регламент",
      render: (plan) => (
        <Link href={buildMaintenancePlanRoute(plan.id)}>{plan.name}</Link>
      ),
    },
    {
      key: "scope",
      title: "Область",
      render: (plan) =>
        plan.scope === PlanScope.EQUIPMENT && plan.equipment_id ? (
          <EquipmentName equipmentId={plan.equipment_id} />
        ) : (
          <span>Категория: {plan.category}</span>
        ),
    },
    {
      key: "interval",
      title: "Периодичность",
      render: (plan) => formatInterval(plan.interval_days),
    },
    {
      key: "first",
      title: "Первый срок",
      render: (plan) => formatDate(plan.first_due_on),
    },
    {
      key: "checklist",
      title: "Операций",
      render: (plan) => plan.checklist.length,
    },
    {
      key: "enabled",
      title: "Состояние",
      render: (plan) => <PlanEnabledLozenge isEnabled={plan.enabled} />,
    },
  ];

  return (
    <div>
      <FilterBar>
        <SearchField
          label="Поиск регламентов"
          value={list.search}
          onChange={list.setSearch}
          placeholder="Название"
        />
        <FilterSelect
          label="Область"
          value={list.filters.scope}
          options={SCOPE_OPTIONS}
          onChange={(value) => list.setFilter("scope", value as PlanScope | "")}
        />
        <FilterSelect
          label="Состояние"
          value={list.filters.enabled}
          options={ENABLED_OPTIONS}
          onChange={(value) =>
            list.setFilter("enabled", value as EnabledFilter)
          }
        />
      </FilterBar>
      {error ? (
        <SectionMessage
          appearance={SectionMessageAppearance.ERROR}
          title="Не удалось загрузить регламенты"
        >
          <p>{getErrorMessage(error)}</p>
        </SectionMessage>
      ) : (
        <>
          <DataTable
            caption="Регламенты технического обслуживания"
            columns={columns}
            rows={data?.items ?? []}
            getRowKey={(plan) => plan.id}
            isLoading={isFetching && !data}
            emptyView={
              <EmptyState
                title="Регламентов не найдено"
                icon={IconName.PLAN}
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

export default PlanTable;
