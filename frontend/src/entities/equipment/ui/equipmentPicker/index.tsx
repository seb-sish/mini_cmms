"use client";

import Select from "@shared/ui/select";
import SearchField from "@shared/ui/searchField";
import useDebouncedValue from "@shared/lib/useDebouncedValue";
import { useEquipmentListQuery } from "../../api/equipmentQueries";
import { useEquipmentQuery } from "../../api/equipmentQueries";
import { ISelectOption } from "@shared/lib/options";
import { MAX_PAGE_SIZE } from "@shared/config";
import { IEquipment } from "../../model/types";
import { ReactElement } from "react";
import { useState } from "react";
import "./style.css";

interface IEquipmentPickerProps {
  label: string;
  value: string;
  onChange: (equipmentId: string) => void;
  isRequired?: boolean;
  isDisabled?: boolean;
  errorMessage?: string;
  placeholder?: string;
}

const DEFAULT_PLACEHOLDER: string = "Выберите оборудование";

export const buildEquipmentOption = (equipment: IEquipment): ISelectOption => ({
  value: equipment.id,
  label: `${equipment.name} (${equipment.inventory_number})`,
});

const EquipmentPicker = ({
  label,
  value,
  onChange,
  isRequired = false,
  isDisabled = false,
  errorMessage,
  placeholder = DEFAULT_PLACEHOLDER,
}: IEquipmentPickerProps): ReactElement => {
  const [search, setSearch] = useState<string>("");
  const debouncedSearch = useDebouncedValue(search.trim());

  const { data: equipmentPage, isFetching } = useEquipmentListQuery(
    { limit: MAX_PAGE_SIZE, offset: 0, q: debouncedSearch || undefined },
    !isDisabled
  );

  const isSelectedInList: boolean = Boolean(
    equipmentPage?.items.some((equipment) => equipment.id === value)
  );
  const { data: selectedEquipment } = useEquipmentQuery(
    value,
    Boolean(value) && !isSelectedInList
  );

  const listOptions: ISelectOption[] = (equipmentPage?.items ?? []).map(
    buildEquipmentOption
  );
  const options: ISelectOption[] =
    selectedEquipment && !isSelectedInList
      ? [buildEquipmentOption(selectedEquipment), ...listOptions]
      : listOptions;

  const helperText: string | undefined =
    equipmentPage && equipmentPage.total > equipmentPage.items.length
      ? `Показаны первые ${equipmentPage.items.length} из ${equipmentPage.total}. Уточните поиск.`
      : undefined;

  return (
    <div className="equipment-picker">
      {!isDisabled && (
        <SearchField
          label={`Поиск: ${label}`}
          value={search}
          onChange={setSearch}
          placeholder="Название или инвентарный номер"
        />
      )}
      <Select
        label={label}
        value={value}
        options={options}
        onChange={onChange}
        placeholder={isFetching ? "Загрузка..." : placeholder}
        isRequired={isRequired}
        isDisabled={isDisabled}
        errorMessage={errorMessage}
        helperText={helperText}
      />
    </div>
  );
};

export default EquipmentPicker;
