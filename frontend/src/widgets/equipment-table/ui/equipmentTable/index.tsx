"use client";

import Link from "next/link";
import Lozenge from "@shared/ui/lozenge";
import FilterBar from "@shared/ui/filterBar";
import DataTable from "@shared/ui/dataTable";
import EmptyState from "@shared/ui/emptyState";
import Pagination from "@shared/ui/pagination";
import SearchField from "@shared/ui/searchField";
import FilterSelect from "@shared/ui/filterSelect";
import useListParams from "@shared/lib/useListParams";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { useEquipmentDictionariesQuery } from "@entities/equipment";
import { EQUIPMENT_STATUS_LABELS } from "@entities/equipment";
import { EquipmentStatusLozenge } from "@entities/equipment";
import { useEquipmentListQuery } from "@entities/equipment";
import { isEquipmentArchived } from "@entities/equipment";
import { EQUIPMENT_STATUSES } from "@entities/equipment";
import { IDataTableColumn } from "@shared/ui/dataTable";
import { LozengeAppearance } from "@shared/ui/lozenge";
import { useViewerPermissions } from "@entities/user";
import { EquipmentStatus } from "@entities/equipment";
import { buildEquipmentRoute } from "@shared/config";
import { ISelectOption } from "@shared/lib/options";
import { buildOptions } from "@shared/lib/options";
import { IEquipment } from "@entities/equipment";
import { getErrorMessage } from "@shared/api";
import { formatDate } from "@shared/lib/date";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import { ReactNode } from "react";

const enum ArchiveFilter {
  ACTIVE = "",
  ARCHIVED = "archived",
  ALL = "all",
}

interface IEquipmentTableFilters {
  category: string;
  location: string;
  status: EquipmentStatus | "";
  archive: ArchiveFilter;
}

interface IEquipmentTableProps {
  emptyAction?: ReactNode;
}

const STATUS_OPTIONS = buildOptions(
  EQUIPMENT_STATUSES,
  EQUIPMENT_STATUS_LABELS
);

const ARCHIVE_OPTIONS: ISelectOption[] = [
  { value: ArchiveFilter.ARCHIVED, label: "Только архив" },
  { value: ArchiveFilter.ALL, label: "Действующее и архив" },
];

const INITIAL_FILTERS: IEquipmentTableFilters = {
  category: "",
  location: "",
  status: "",
  archive: ArchiveFilter.ACTIVE,
};

const toStringOptions = (values: string[] = []): ISelectOption[] =>
  values.map((value) => ({ value, label: value }));

const EquipmentTable = ({
  emptyAction,
}: IEquipmentTableProps): ReactElement => {
  const permissions = useViewerPermissions();
  const list = useListParams(INITIAL_FILTERS);
  const { data: dictionaries } = useEquipmentDictionariesQuery();

  const { data, isFetching, error } = useEquipmentListQuery({
    limit: list.limit,
    offset: list.offset,
    q: list.query,
    category: list.filters.category || undefined,
    location: list.filters.location || undefined,
    status: list.filters.status,
    include_archived: list.filters.archive === ArchiveFilter.ALL || undefined,
    is_archived: list.filters.archive === ArchiveFilter.ARCHIVED || undefined,
  });

  const columns: IDataTableColumn<IEquipment>[] = [
    {
      key: "name",
      title: "Наименование",
      render: (equipment) => (
        <Link href={buildEquipmentRoute(equipment.id)}>{equipment.name}</Link>
      ),
    },
    {
      key: "inventory",
      title: "Инв. номер",
      render: (equipment) => (
        <span className="code-text">{equipment.inventory_number}</span>
      ),
    },
    {
      key: "category",
      title: "Категория",
      render: (equipment) => equipment.category,
    },
    {
      key: "location",
      title: "Цех / местоположение",
      render: (equipment) => equipment.location,
    },
    {
      key: "status",
      title: "Статус",
      render: (equipment) =>
        isEquipmentArchived(equipment) ? (
          <Lozenge
            label="В архиве"
            appearance={LozengeAppearance.DEFAULT}
            isBold
          />
        ) : (
          <EquipmentStatusLozenge status={equipment.status} />
        ),
    },
    {
      key: "commissioned",
      title: "Ввод в эксплуатацию",
      render: (equipment) => formatDate(equipment.commissioned_on),
    },
  ];

  return (
    <div>
      <FilterBar>
        <SearchField
          label="Поиск оборудования"
          value={list.search}
          onChange={list.setSearch}
          placeholder="Наименование или инв. номер"
        />
        <FilterSelect
          label="Категория"
          value={list.filters.category}
          options={toStringOptions(dictionaries?.categories)}
          onChange={(value) => list.setFilter("category", value)}
        />
        <FilterSelect
          label="Местоположение"
          value={list.filters.location}
          options={toStringOptions(dictionaries?.locations)}
          onChange={(value) => list.setFilter("location", value)}
        />
        <FilterSelect
          label="Статус"
          value={list.filters.status}
          options={STATUS_OPTIONS}
          onChange={(value) =>
            list.setFilter("status", value as EquipmentStatus | "")
          }
        />
        {permissions.canManageEquipment && (
          <FilterSelect
            label="Архив"
            value={list.filters.archive}
            options={ARCHIVE_OPTIONS}
            allLabel="Только действующее"
            onChange={(value) =>
              list.setFilter("archive", value as ArchiveFilter)
            }
          />
        )}
      </FilterBar>
      {error ? (
        <SectionMessage
          appearance={SectionMessageAppearance.ERROR}
          title="Не удалось загрузить оборудование"
        >
          <p>{getErrorMessage(error)}</p>
        </SectionMessage>
      ) : (
        <>
          <DataTable
            caption="Оборудование"
            columns={columns}
            rows={data?.items ?? []}
            getRowKey={(equipment) => equipment.id}
            isLoading={isFetching && !data}
            emptyView={
              <EmptyState
                title="Оборудование не найдено"
                description="Измените условия поиска или добавьте карточку оборудования."
                icon={IconName.EQUIPMENT}
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

export default EquipmentTable;
