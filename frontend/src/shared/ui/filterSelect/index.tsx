"use client";

import { ISelectOption } from "@shared/lib/options";
import { ReactElement } from "react";
import { ChangeEvent } from "react";
import "@shared/ui/formField/style.css";
import "@shared/ui/select/style.css";
import "./style.css";

interface IFilterSelectProps {
  label: string;
  value: string;
  options: ISelectOption[];
  onChange: (value: string) => void;
  allLabel?: string;
}

const DEFAULT_ALL_LABEL: string = "Все";

const FilterSelect = ({
  label,
  value,
  options,
  onChange,
  allLabel = DEFAULT_ALL_LABEL,
}: IFilterSelectProps): ReactElement => {
  const onHandleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onChange(event.target.value);
  };

  const activeClassname: string = value ? "active" : "";

  return (
    <label className={`filter-select ${activeClassname}`}>
      <span className="filter-select-label body-small">{label}</span>
      <select
        className="form-control select"
        value={value}
        onChange={onHandleChange}
      >
        <option value="">{allLabel}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
};

export default FilterSelect;
