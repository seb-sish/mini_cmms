import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

export interface IDescriptionItem {
  label: string;
  value: ReactNode;
}

interface IDescriptionListProps {
  items: IDescriptionItem[];
}

const EMPTY_VALUE: string = "Не указано";

const DescriptionList = ({ items }: IDescriptionListProps): ReactElement => {
  return (
    <dl className="description-list">
      {items.map(({ label, value }) => (
        <div key={label} className="description-list-row">
          <dt className="description-list-label">{label}</dt>
          <dd className="description-list-value">
            {value ?? <span className="text-subtlest">{EMPTY_VALUE}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
};

export default DescriptionList;
