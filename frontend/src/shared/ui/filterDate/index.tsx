"use client";

import { ReactElement } from "react";
import { ChangeEvent } from "react";
import "@shared/ui/formField/style.css";
import "@shared/ui/filterSelect/style.css";

interface IFilterDateProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
}

const FilterDate = ({
  label,
  value,
  onChange,
  min,
  max,
}: IFilterDateProps): ReactElement => {
  const onHandleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value);
  };

  const activeClassname: string = value ? "active" : "";

  return (
    <label className={`filter-select ${activeClassname}`}>
      <span className="filter-select-label body-small">{label}</span>
      <input
        className="form-control"
        type="date"
        value={value}
        min={min}
        max={max}
        onChange={onHandleChange}
      />
    </label>
  );
};

export default FilterDate;
