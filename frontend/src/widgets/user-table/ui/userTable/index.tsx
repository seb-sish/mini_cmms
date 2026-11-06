"use client";

import Link from "next/link";
import Avatar from "@shared/ui/avatar";
import FilterBar from "@shared/ui/filterBar";
import DataTable from "@shared/ui/dataTable";
import EmptyState from "@shared/ui/emptyState";
import Pagination from "@shared/ui/pagination";
import SearchField from "@shared/ui/searchField";
import FilterSelect from "@shared/ui/filterSelect";
import useListParams from "@shared/lib/useListParams";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { IDataTableColumn } from "@shared/ui/dataTable";
import { USER_STATUS_LABELS } from "@entities/user";
import { UserStatusLozenge } from "@entities/user";
import { buildOptions } from "@shared/lib/options";
import { USER_ROLE_LABELS } from "@entities/user";
import { formatDateTime } from "@shared/lib/date";
import { buildUserRoute } from "@shared/config";
import { useUsersQuery } from "@entities/user";
import { USER_STATUSES } from "@entities/user";
import { getErrorMessage } from "@shared/api";
import { USER_ROLES } from "@entities/user";
import { UserStatus } from "@entities/user";
import { IconName } from "@shared/ui/icon";
import { UserRole } from "@entities/user";
import { IUser } from "@entities/user";
import { ReactElement } from "react";
import "./style.css";

interface IUserTableFilters {
  role: UserRole | "";
  status: UserStatus | "";
}

const ROLE_OPTIONS = buildOptions(USER_ROLES, USER_ROLE_LABELS);
const STATUS_OPTIONS = buildOptions(USER_STATUSES, USER_STATUS_LABELS);
const INITIAL_FILTERS: IUserTableFilters = { role: "", status: "" };

const UserTable = (): ReactElement => {
  const list = useListParams(INITIAL_FILTERS);

  const { data, isFetching, error } = useUsersQuery({
    limit: list.limit,
    offset: list.offset,
    q: list.query,
    role: list.filters.role,
    status: list.filters.status,
  });

  const columns: IDataTableColumn<IUser>[] = [
    {
      key: "login",
      title: "Логин",
      render: (user) => (
        <span className="user-table-login">
          <Avatar name={user.login} />
          <Link href={buildUserRoute(user.id)}>{user.login}</Link>
        </span>
      ),
    },
    {
      key: "role",
      title: "Роль",
      render: (user) => USER_ROLE_LABELS[user.role],
    },
    {
      key: "status",
      title: "Состояние",
      render: (user) => <UserStatusLozenge status={user.status} />,
    },
    {
      key: "created",
      title: "Создан",
      render: (user) => (
        <span className="body-small text-subtle">
          {formatDateTime(user.created_at)}
        </span>
      ),
    },
  ];

  return (
    <div>
      <FilterBar>
        <SearchField
          label="Поиск по логину"
          value={list.search}
          onChange={list.setSearch}
          placeholder="Логин"
        />
        <FilterSelect
          label="Роль"
          value={list.filters.role}
          options={ROLE_OPTIONS}
          onChange={(value) => list.setFilter("role", value as UserRole | "")}
        />
        <FilterSelect
          label="Состояние"
          value={list.filters.status}
          options={STATUS_OPTIONS}
          onChange={(value) =>
            list.setFilter("status", value as UserStatus | "")
          }
        />
      </FilterBar>
      {error ? (
        <SectionMessage
          appearance={SectionMessageAppearance.ERROR}
          title="Не удалось загрузить пользователей"
        >
          <p>{getErrorMessage(error)}</p>
        </SectionMessage>
      ) : (
        <>
          <DataTable
            caption="Пользователи"
            columns={columns}
            rows={data?.items ?? []}
            getRowKey={(user) => user.id}
            isLoading={isFetching && !data}
            emptyView={
              <EmptyState
                title="Пользователи не найдены"
                icon={IconName.USERS}
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

export default UserTable;
