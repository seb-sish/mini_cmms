import { buildEquipmentFixture } from "@entities/equipment/testing";
import { buildEquipmentPatchPayload } from "./equipmentForm";
import { toEquipmentCreatePayload } from "./equipmentForm";
import { INITIAL_EQUIPMENT_VALUES } from "./equipmentForm";
import { validateEquipmentForm } from "./equipmentForm";
import { toEquipmentFormValues } from "./equipmentForm";
import { EquipmentStatus } from "@entities/equipment";

const TODAY = "2026-10-29";

describe("equipment form", () => {
  it("requires all card fields", () => {
    const errors = validateEquipmentForm(INITIAL_EQUIPMENT_VALUES, TODAY);

    expect(errors.name).toBe("Обязательное поле.");
    expect(errors.inventory_number).toBe("Обязательное поле.");
    expect(errors.category).toBe("Обязательное поле.");
    expect(errors.location).toBe("Обязательное поле.");
    expect(errors.commissioned_on).toBe("Обязательное поле.");
  });

  it("rejects commissioning date in the future", () => {
    const values = {
      ...toEquipmentFormValues(buildEquipmentFixture()),
      commissioned_on: "2026-10-30",
    };

    expect(validateEquipmentForm(values, TODAY).commissioned_on).toBe(
      "Дата не может быть позже сегодняшней."
    );
  });

  it("trims text fields in create payload", () => {
    const payload = toEquipmentCreatePayload({
      ...INITIAL_EQUIPMENT_VALUES,
      name: "  Пресс  ",
      inventory_number: " INV-7 ",
      category: " Прессы ",
      location: " Цех 2 ",
      commissioned_on: "2025-01-01",
    });

    expect(payload).toEqual({
      name: "Пресс",
      inventory_number: "INV-7",
      category: "Прессы",
      location: "Цех 2",
      commissioned_on: "2025-01-01",
      status: EquipmentStatus.OPERATIONAL,
    });
  });

  it("sends only changed fields in PATCH payload", () => {
    const equipment = buildEquipmentFixture();
    const values = {
      ...toEquipmentFormValues(equipment),
      location: " Цех 3 ",
      status: EquipmentStatus.UNDER_REPAIR,
    };

    expect(buildEquipmentPatchPayload(equipment, values)).toEqual({
      location: "Цех 3",
      status: EquipmentStatus.UNDER_REPAIR,
    });
    expect(
      buildEquipmentPatchPayload(equipment, toEquipmentFormValues(equipment))
    ).toEqual({});
  });
});
