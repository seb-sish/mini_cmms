"use client";

import Button from "@shared/ui/button";
import { ButtonAppearance } from "@shared/ui/button";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import "./style.css";

interface IPaginationProps {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}

export const getPageRange = (
  total: number,
  limit: number,
  offset: number
): string => {
  if (total === 0) return "0 из 0";

  const from = Math.min(offset + 1, total);
  const to = Math.min(offset + limit, total);

  return `${from}-${to} из ${total}`;
};

const Pagination = ({
  total,
  limit,
  offset,
  onChange,
}: IPaginationProps): ReactElement | null => {
  if (total <= limit && offset === 0) return null;

  const currentPage: number = Math.floor(offset / limit) + 1;
  const totalPages: number = Math.max(1, Math.ceil(total / limit));

  const handlePrevious = () => {
    onChange(Math.max(0, offset - limit));
  };

  const handleNext = () => {
    onChange(offset + limit);
  };

  return (
    <nav className="pagination" aria-label="Постраничная навигация">
      <span className="pagination-range body-small text-subtle">
        {getPageRange(total, limit, offset)}
      </span>
      <Button
        label="Предыдущая страница"
        appearance={ButtonAppearance.SUBTLE}
        iconBefore={IconName.CHEVRON_LEFT}
        isIconOnly
        isDisabled={currentPage <= 1}
        onClick={handlePrevious}
      />
      <span className="pagination-page body-small" aria-current="page">
        {currentPage} / {totalPages}
      </span>
      <Button
        label="Следующая страница"
        appearance={ButtonAppearance.SUBTLE}
        iconBefore={IconName.CHEVRON_RIGHT}
        isIconOnly
        isDisabled={currentPage >= totalPages}
        onClick={handleNext}
      />
    </nav>
  );
};

export default Pagination;
