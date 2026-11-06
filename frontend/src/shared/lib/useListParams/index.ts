"use client";

import useDebouncedValue from "@shared/lib/useDebouncedValue";
import { DEFAULT_PAGE_SIZE } from "@shared/config";
import { useState } from "react";

interface IListState<TFilters> {
  filters: TFilters;
  offset: number;
}

const useListParams = <TFilters extends object>(
  initialFilters: TFilters,
  pageSize: number = DEFAULT_PAGE_SIZE
) => {
  const [state, setState] = useState<IListState<TFilters>>({
    filters: initialFilters,
    offset: 0,
  });
  const [search, setSearchValue] = useState<string>("");
  const debouncedSearch: string = useDebouncedValue(search.trim());

  const setFilter = <TKey extends keyof TFilters>(
    key: TKey,
    value: TFilters[TKey]
  ) => {
    setState((prev) => ({
      filters: { ...prev.filters, [key]: value },
      offset: 0,
    }));
  };

  const setSearch = (value: string) => {
    setSearchValue(value);
    setState((prev) => ({ ...prev, offset: 0 }));
  };

  const setOffset = (offset: number) => {
    setState((prev) => ({ ...prev, offset }));
  };

  const resetFilters = () => {
    setSearchValue("");
    setState({ filters: initialFilters, offset: 0 });
  };

  return {
    filters: state.filters,
    search,
    query: debouncedSearch || undefined,
    limit: pageSize,
    offset: state.offset,
    setFilter,
    setSearch,
    setOffset,
    resetFilters,
  };
};

export default useListParams;
