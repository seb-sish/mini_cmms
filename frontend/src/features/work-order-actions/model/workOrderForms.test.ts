import { buildWorkOrderFixture } from "@entities/work-order/testing";
import { validateCancellationReason } from "./workOrderForms";
import { buildWorkOrderPatchPayload } from "./workOrderForms";
import { toWorkOrderEditValues } from "./workOrderForms";
import { WorkOrderPriority } from "@entities/work-order";
import { validateReplacedPart } from "./workOrderForms";
import { validateCompleteForm } from "./workOrderForms";
import { validateAssigneeId } from "./workOrderForms";
import { toCompletePayload } from "./workOrderForms";

const workOrder = buildWorkOrderFixture();

describe("work order forms", () => {
  it("sends only changed fields in PATCH payload", () => {
    expect(
      buildWorkOrderPatchPayload(workOrder, {
        title: `  ${workOrder.title}  `,
        description: workOrder.description,
        priority: WorkOrderPriority.HIGH,
      })
    ).toEqual({ priority: WorkOrderPriority.HIGH });
  });

  it("returns empty payload when nothing changed", () => {
    expect(
      buildWorkOrderPatchPayload(workOrder, toWorkOrderEditValues(workOrder))
    ).toEqual({});
  });

  it("requires result and forbids unsaved replaced part draft on completion", () => {
    expect(
      validateCompleteForm({ result: " ", replacedParts: [], partDraft: "" })
        .result
    ).toBe("Обязательное поле.");
    expect(
      validateCompleteForm({
        result: "Готово",
        replacedParts: [],
        partDraft: "Болт",
      }).partDraft
    ).toBeDefined();
    expect(
      validateCompleteForm({
        result: "Готово",
        replacedParts: ["Болт"],
        partDraft: "",
      })
    ).toEqual({
      result: undefined,
      partDraft: undefined,
    });
  });

  it("validates replaced parts length and count", () => {
    expect(validateReplacedPart("  ", [])).toBe("Обязательное поле.");
    expect(
      validateReplacedPart(
        "Подшипник",
        Array.from({ length: 100 }, () => "x")
      )
    ).toBe("Не более 100 деталей.");
    expect(validateReplacedPart("Подшипник", [])).toBeUndefined();
  });

  it("normalizes completion payload", () => {
    expect(
      toCompletePayload({
        result: "  Готово  ",
        replacedParts: ["Болт"],
        partDraft: "",
      })
    ).toEqual({
      result: "Готово",
      replaced_parts: ["Болт"],
    });
  });

  it("requires cancellation reason", () => {
    expect(validateCancellationReason("   ")).toBe("Обязательное поле.");
    expect(validateCancellationReason("Создана по ошибке")).toBeUndefined();
  });

  it("validates technician identifier", () => {
    expect(validateAssigneeId("")).toBe("Выберите исполнителя.");
    expect(validateAssigneeId("not-a-uuid")).toBe(
      "Некорректный идентификатор техника."
    );
    expect(
      validateAssigneeId(" 9f1dc502-92e6-4eca-af95-6ec851ca4d8e ")
    ).toBeUndefined();
  });
});
