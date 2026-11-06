import { buildMaintenancePlanFixture } from "@entities/maintenance-plan/testing";
import { PlanScope } from "@entities/maintenance-plan";
import { createChecklistDraftItem } from "./planForm";
import { buildInitialPlanValues } from "./planForm";
import { buildPlanPatchPayload } from "./planForm";
import { toPlanCreatePayload } from "./planForm";
import { hasPlanFormErrors } from "./planForm";
import { validateChecklist } from "./planForm";
import { validatePlanForm } from "./planForm";
import { toPlanFormValues } from "./planForm";

const TODAY = "2026-10-29";

describe("maintenance plan form", () => {
  it("requires equipment for EQUIPMENT scope and category for CATEGORY scope", () => {
    const equipmentErrors = validatePlanForm(
      { ...buildInitialPlanValues(TODAY), name: "ТО" },
      false
    );
    const categoryErrors = validatePlanForm(
      {
        ...buildInitialPlanValues(TODAY),
        name: "ТО",
        scope: PlanScope.CATEGORY,
      },
      false
    );

    expect(equipmentErrors.equipment_id).toBe("Выберите оборудование.");
    expect(categoryErrors.category).toBe("Обязательное поле.");
    expect(categoryErrors.equipment_id).toBeUndefined();
  });

  it("validates positive interval within contract range", () => {
    const values = {
      ...buildInitialPlanValues(TODAY),
      name: "ТО",
      equipment_id: "eq",
    };

    expect(
      validatePlanForm({ ...values, interval_days: "0" }, false).interval_days
    ).toBe("Допустимо от 1 до 3650.");
    expect(
      validatePlanForm({ ...values, interval_days: "3650" }, false)
        .interval_days
    ).toBeUndefined();
  });

  it("requires at least one checklist operation", () => {
    expect(validateChecklist([]).checklist).toBe(
      "Добавьте хотя бы одну операцию."
    );
  });

  it("rejects duplicate titles after whitespace normalization", () => {
    const first = createChecklistDraftItem("Проверить  масло");
    const duplicate = createChecklistDraftItem(" Проверить масло ");
    const tooShort = createChecklistDraftItem("a");

    const { checklistItems } = validateChecklist([first, duplicate, tooShort]);

    expect(checklistItems?.[first.key]).toBeUndefined();
    expect(checklistItems?.[duplicate.key]).toBe(
      "Такая операция уже есть в списке."
    );
    expect(checklistItems?.[tooShort.key]).toBe("Минимальная длина: 2 симв.");
  });

  it("treats titles differing by case as different", () => {
    expect(
      validateChecklist([
        createChecklistDraftItem("Масло"),
        createChecklistDraftItem("масло"),
      ])
    ).toEqual({});
  });

  it("detects item level errors", () => {
    expect(hasPlanFormErrors({ checklistItems: { a: "error" } })).toBe(true);
    expect(hasPlanFormErrors({ checklistItems: {}, name: undefined })).toBe(
      false
    );
  });

  it("builds create payload with sequential order and exclusive scope", () => {
    const payload = toPlanCreatePayload({
      ...buildInitialPlanValues(TODAY),
      name: " ТО насосов ",
      scope: PlanScope.CATEGORY,
      equipment_id: "leftover",
      category: " Насосы ",
      interval_days: "45",
      checklist: [
        createChecklistDraftItem(" Осмотр  уплотнений "),
        createChecklistDraftItem("Замер вибрации", false),
      ],
    });

    expect(payload).toEqual({
      name: "ТО насосов",
      scope: PlanScope.CATEGORY,
      equipment_id: null,
      category: "Насосы",
      interval_days: 45,
      first_due_on: TODAY,
      checklist: [
        { title: "Осмотр уплотнений", required: true, order: 1 },
        { title: "Замер вибрации", required: false, order: 2 },
      ],
    });
  });

  it("restores checklist order when editing and detects changes", () => {
    const plan = buildMaintenancePlanFixture();
    const values = toPlanFormValues(plan);

    expect(values.checklist.map((item) => item.title)).toEqual([
      "Проверить уровень масла",
      "Очистить фильтр",
    ]);
    expect(buildPlanPatchPayload(plan, values)).toEqual({});
    expect(
      buildPlanPatchPayload(plan, { ...values, interval_days: "60" })
    ).toEqual({ interval_days: 60 });
    expect(
      buildPlanPatchPayload(plan, {
        ...values,
        checklist: [...values.checklist].reverse(),
      }).checklist
    ).toEqual([
      { title: "Очистить фильтр", required: false, order: 1 },
      { title: "Проверить уровень масла", required: true, order: 2 },
    ]);
  });
});
