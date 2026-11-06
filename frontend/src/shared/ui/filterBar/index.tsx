import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

interface IFilterBarProps {
  children: ReactNode;
}

const FilterBar = ({ children }: IFilterBarProps): ReactElement => {
  return (
    <div className="filter-bar" role="search">
      {children}
    </div>
  );
};

export default FilterBar;
