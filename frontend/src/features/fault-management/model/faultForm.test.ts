import { buildFaultFixture } from "@entities/fault/testing";
import { buildUserFixture } from "@entities/user/testing";
import { buildInitialFaultValues } from "./faultForm";
import { buildFaultPatchPayload } from "./faultForm";
import { toFaultCreatePayload } from "./faultForm";
import { validateFaultForm } from "./faultForm";
import { toFaultFormValues } from "./faultForm";
import { FaultSeverity } from "@entities/fault";
import { FaultStatus } from "@entities/fault";
import { canEditFault } from "./faultForm";
import { UserRole } from "@entities/user";

const TODAY = "2026-10-29";

describe("fault form", () => {
  it("defaults detection date to today and requires equipment and severity", () => {
    const values = buildInitialFaultValues("", TODAY);
    const errors = validateFaultForm(
      { ...values, description: "Течь масла" },
      TODAY
    );

    expect(values.detected_on).toBe(TODAY);
    expect(errors.equipment_id).toBe("Выберите оборудование.");
    expect(errors.severity).toBe("Выберите критичность.");
  });

  it("validates description length and future date", () => {
    const errors = validateFaultForm(
      {
        equipment_id: "eq",
        description: "abc",
        detected_on: "2026-10-30",
        severity: FaultSeverity.LOW,
      },
      TODAY
    );

    expect(errors.description).toBe("Минимальная длина: 5 симв.");
    expect(errors.detected_on).toBe("Дата не может быть позже сегодняшней.");
  });

  it("normalizes create payload", () => {
    expect(
      toFaultCreatePayload({
        equipment_id: "eq",
        description: "  Течь масла  ",
        detected_on: TODAY,
        severity: FaultSeverity.CRITICAL,
      })
    ).toEqual({
      equipment_id: "eq",
      description: "Течь масла",
      detected_on: TODAY,
      severity: FaultSeverity.CRITICAL,
    });
  });

  it("sends only changed fields in PATCH payload", () => {
    const fault = buildFaultFixture();

    expect(
      buildFaultPatchPayload(fault, {
        ...toFaultFormValues(fault),
        severity: FaultSeverity.CRITICAL,
      })
    ).toEqual({
      severity: FaultSeverity.CRITICAL,
    });
    expect(buildFaultPatchPayload(fault, toFaultFormValues(fault))).toEqual({});
  });

  it("allows editing only open faults by engineer or the author operator", () => {
    const openFault = buildFaultFixture({ author_id: "operator-1" });

    expect(
      canEditFault(buildUserFixture({ role: UserRole.ENGINEER }), openFault)
    ).toBe(true);
    expect(
      canEditFault(
        buildUserFixture({ id: "operator-1", role: UserRole.OPERATOR }),
        openFault
      )
    ).toBe(true);
    expect(
      canEditFault(
        buildUserFixture({ id: "operator-2", role: UserRole.OPERATOR }),
        openFault
      )
    ).toBe(false);
    expect(
      canEditFault(buildUserFixture({ role: UserRole.TECHNICIAN }), openFault)
    ).toBe(false);
    expect(
      canEditFault(
        buildUserFixture({ role: UserRole.ENGINEER }),
        buildFaultFixture({ status: FaultStatus.IN_PROGRESS })
      )
    ).toBe(false);
  });
});
