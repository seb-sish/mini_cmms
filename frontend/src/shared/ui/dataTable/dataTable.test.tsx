import DataTable from "./index";
import userEvent from "@testing-library/user-event";
import { render } from "@testing-library/react";
import { screen } from "@testing-library/react";
import { getNextSortValue } from "./index";
import { IDataTableColumn } from "./index";

interface IRow {
  id: string;
  name: string;
}

const COLUMNS: IDataTableColumn<IRow>[] = [
  {
    key: "name",
    title: "Название",
    render: (row) => row.name,
    sortKey: "name",
  },
];

describe("DataTable", () => {
  it("toggles sort direction for the same key", () => {
    expect(getNextSortValue("-created_at", "status")).toBe("status");
    expect(getNextSortValue("status", "status")).toBe("-status");
    expect(getNextSortValue("-status", "status")).toBe("status");
  });

  it("renders rows", () => {
    render(
      <DataTable
        caption="Список"
        columns={COLUMNS}
        rows={[{ id: "1", name: "Пресс" }]}
        getRowKey={(row) => row.id}
      />
    );

    expect(screen.getByRole("cell", { name: "Пресс" })).toBeInTheDocument();
  });

  it("shows empty view when there are no rows", () => {
    render(
      <DataTable
        caption="Список"
        columns={COLUMNS}
        rows={[]}
        getRowKey={(row) => row.id}
        emptyView={<p>Ничего не найдено</p>}
      />
    );

    expect(screen.getByText("Ничего не найдено")).toBeInTheDocument();
  });

  it("requests sorting from sortable header", async () => {
    const handleSortChange = vi.fn();

    render(
      <DataTable
        caption="Список"
        columns={COLUMNS}
        rows={[]}
        getRowKey={(row) => row.id}
        sortValue="name"
        onSortChange={handleSortChange}
      />
    );

    expect(screen.getByRole("columnheader")).toHaveAttribute(
      "aria-sort",
      "ascending"
    );

    await userEvent.click(screen.getByRole("button", { name: /Название/ }));

    expect(handleSortChange).toHaveBeenCalledWith("-name");
  });
});
