"use client";

import Icon from "@shared/ui/icon";
import Spinner from "@shared/ui/spinner";
import { SpinnerSize } from "@shared/ui/spinner";
import { IconName } from "@shared/ui/icon";
import { IconSize } from "@shared/ui/icon";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

export interface IDataTableColumn<TRow> {
  key: string;
  title: string;
  render: (row: TRow) => ReactNode;
  width?: string;
  sortKey?: string;
}

interface IDataTableProps<TRow> {
  caption: string;
  columns: IDataTableColumn<TRow>[];
  rows: TRow[];
  getRowKey: (row: TRow) => string;
  isLoading?: boolean;
  emptyView?: ReactNode;
  sortValue?: string;
  onSortChange?: (sortValue: string) => void;
}

const DESCENDING_PREFIX = "-";

export const getNextSortValue = (
  currentSort: string | undefined,
  sortKey: string
): string =>
  currentSort === sortKey ? `${DESCENDING_PREFIX}${sortKey}` : sortKey;

const getSortState = (
  currentSort: string | undefined,
  sortKey: string
): "ascending" | "descending" | "none" => {
  if (currentSort === sortKey) return "ascending";
  if (currentSort === `${DESCENDING_PREFIX}${sortKey}`) return "descending";

  return "none";
};

const DataTable = <TRow,>({
  caption,
  columns,
  rows,
  getRowKey,
  isLoading = false,
  emptyView,
  sortValue,
  onSortChange,
}: IDataTableProps<TRow>): ReactElement => {
  const isEmpty: boolean = !isLoading && rows.length === 0;

  const renderHeaderCell = (column: IDataTableColumn<TRow>) => {
    if (!column.sortKey || !onSortChange) return column.title;

    const sortKey: string = column.sortKey;
    const sortState = getSortState(sortValue, sortKey);
    const sortIcon: IconName =
      sortState === "descending"
        ? IconName.CHEVRON_DOWN
        : IconName.PRIORITY_HIGH;

    const handleSortClick = () => {
      onSortChange(getNextSortValue(sortValue, sortKey));
    };

    return (
      <button
        className="data-table-sort-button"
        type="button"
        onClick={handleSortClick}
      >
        {column.title}
        <span className={`data-table-sort-icon ${sortState}`}>
          <Icon name={sortIcon} size={IconSize.SMALL} />
        </span>
      </button>
    );
  };

  return (
    <div className="data-table-wrapper" aria-busy={isLoading}>
      <table className="data-table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                style={column.width ? { width: column.width } : undefined}
                aria-sort={
                  column.sortKey && onSortChange
                    ? getSortState(sortValue, column.sortKey)
                    : undefined
                }
              >
                {renderHeaderCell(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={getRowKey(row)}>
              {columns.map((column) => (
                <td key={column.key}>{column.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {isLoading && (
        <div className="data-table-loading">
          <Spinner size={SpinnerSize.LARGE} />
        </div>
      )}
      {isEmpty && emptyView}
    </div>
  );
};

export default DataTable;
