"use client";

import Icon from "@shared/ui/icon";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import { ChangeEvent } from "react";
import "@shared/ui/formField/style.css";
import "./style.css";

interface ISearchFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

const SearchField = ({
  label,
  value,
  onChange,
  placeholder,
}: ISearchFieldProps): ReactElement => {
  const onHandleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value);
  };

  return (
    <div className="search-field">
      <span className="search-field-icon">
        <Icon name={IconName.SEARCH} />
      </span>
      <input
        className="form-control search-field-input"
        type="search"
        value={value}
        placeholder={placeholder}
        aria-label={label}
        onChange={onHandleChange}
      />
    </div>
  );
};

export default SearchField;
