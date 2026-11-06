import Tag from "@shared/ui/tag";
import { ReactElement } from "react";
import "./style.css";

interface IReplacedPartsListProps {
  parts: string[];
}

const ReplacedPartsList = ({
  parts,
}: IReplacedPartsListProps): ReactElement => {
  if (parts.length === 0)
    return <span className="text-subtlest">Детали не заменялись</span>;

  return (
    <ul className="replaced-parts-list">
      {parts.map((part, index) => (
        <li key={`${part}-${index}`}>
          <Tag label={part} />
        </li>
      ))}
    </ul>
  );
};

export default ReplacedPartsList;
