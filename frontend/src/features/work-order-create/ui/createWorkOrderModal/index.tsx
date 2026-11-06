"use client";

import Select from "@shared/ui/select";
import TextArea from "@shared/ui/textArea";
import TextField from "@shared/ui/textField";
import FormModal from "@shared/ui/formModal";
import { useMaintenanceSchedulesQuery } from "@entities/maintenance-schedule";
import { buildInitialWorkOrderValues } from "../../model/workOrderCreateForm";
import { validateWorkOrderCreateForm } from "../../model/workOrderCreateForm";
import { IWorkOrderCreateFormValues } from "../../model/workOrderCreateForm";
import { toWorkOrderCreatePayload } from "../../model/workOrderCreateForm";
import { IWorkOrderCreateInitial } from "../../model/workOrderCreateForm";
import { maintenanceScheduleKeys } from "@entities/maintenance-schedule";
import { useMaintenancePlansQuery } from "@entities/maintenance-plan";
import { WORK_ORDER_PRIORITY_LABELS } from "@entities/work-order";
import { WORK_ORDER_TYPE_LABELS } from "@entities/work-order";
import { WORK_ORDER_PRIORITIES } from "@entities/work-order";
import { WORK_ORDER_LIMITS } from "@entities/work-order";
import { WorkOrderPriority } from "@entities/work-order";
import { WORK_ORDER_TYPES } from "@entities/work-order";
import { useQueryClient } from "@tanstack/react-query";
import { createWorkOrder } from "@entities/work-order";
import { useViewerPermissions } from "@entities/user";
import { EquipmentPicker } from "@entities/equipment";
import { workOrderKeys } from "@entities/work-order";
import { WorkOrderType } from "@entities/work-order";
import { useMutation } from "@tanstack/react-query";
import { ISelectOption } from "@shared/lib/options";
import { buildOptions } from "@shared/lib/options";
import { IWorkOrder } from "@entities/work-order";
import { useFaultsQuery } from "@entities/fault";
import { FlagAppearance } from "@shared/ui/flag";
import { useFormFields } from "@shared/lib/form";
import { MAX_PAGE_SIZE } from "@shared/config";
import { getErrorMessage } from "@shared/api";
import { FaultStatus } from "@entities/fault";
import { formatDate } from "@shared/lib/date";
import { getFieldErrors } from "@shared/api";
import { hasErrors } from "@shared/lib/form";
import { faultKeys } from "@entities/fault";
import { useFlags } from "@shared/ui/flag";
import { ReactElement } from "react";

interface ICreateWorkOrderModalProps {
  initial?: IWorkOrderCreateInitial;
  onClose: () => void;
  onCreated?: (workOrder: IWorkOrder) => void;
}

const PRIORITY_OPTIONS = buildOptions(
  WORK_ORDER_PRIORITIES,
  WORK_ORDER_PRIORITY_LABELS
);
const TYPE_OPTIONS = buildOptions(WORK_ORDER_TYPES, WORK_ORDER_TYPE_LABELS);
const FAULT_DESCRIPTION_PREVIEW_LENGTH = 70;

const CreateWorkOrderModal = ({
  initial = {},
  onClose,
  onCreated,
}: ICreateWorkOrderModalProps): ReactElement => {
  const queryClient = useQueryClient();
  const { showFlag } = useFlags();
  const permissions = useViewerPermissions();
  const { values, errors, setErrors, setFieldValue } =
    useFormFields<IWorkOrderCreateFormValues>(
      buildInitialWorkOrderValues(initial)
    );
  const isRepair: boolean = values.type === WorkOrderType.REPAIR;
  const isSourceLocked: boolean = Boolean(
    initial.faultId || initial.scheduleId
  );

  const { data: openFaults } = useFaultsQuery(
    {
      limit: MAX_PAGE_SIZE,
      offset: 0,
      equipment_id: values.equipment_id,
      status: FaultStatus.OPEN,
    },
    isRepair && Boolean(values.equipment_id)
  );
  const { data: schedules } = useMaintenanceSchedulesQuery(
    {
      limit: MAX_PAGE_SIZE,
      offset: 0,
      equipment_id: values.equipment_id,
      is_active: true,
    },
    !isRepair && Boolean(values.equipment_id)
  );
  const { data: plans } = useMaintenancePlansQuery(
    { limit: MAX_PAGE_SIZE, offset: 0 },
    !isRepair
  );

  const faultOptions: ISelectOption[] = (openFaults?.items ?? []).map(
    (fault) => ({
      value: fault.id,
      label: `${formatDate(fault.detected_on)}: ${fault.description.slice(0, FAULT_DESCRIPTION_PREVIEW_LENGTH)}`,
    })
  );

  const scheduleOptions: ISelectOption[] = (schedules?.items ?? [])
    .filter(
      (schedule) =>
        !schedule.has_current_work_order || schedule.id === values.schedule_id
    )
    .map((schedule) => {
      const planName =
        plans?.items.find((plan) => plan.id === schedule.plan_id)?.name ??
        "Регламент";

      return {
        value: schedule.id,
        label: `${planName}, срок ${formatDate(schedule.next_due_on)}`,
      };
    });

  const createMutation = useMutation({
    mutationFn: () => createWorkOrder(toWorkOrderCreatePayload(values)),
    onSuccess: (workOrder) => {
      queryClient.setQueryData(workOrderKeys.detail(workOrder.id), workOrder);
      queryClient.invalidateQueries({ queryKey: workOrderKeys.lists() });
      queryClient.invalidateQueries({ queryKey: maintenanceScheduleKeys.all });
      queryClient.invalidateQueries({ queryKey: faultKeys.all });
      showFlag({
        appearance: FlagAppearance.SUCCESS,
        title: "Заявка создана",
        description: `${workOrder.number}: статус "Создана"`,
      });
      onCreated?.(workOrder);
      onClose();
    },
    onError: (error) => {
      setErrors((prev) => ({ ...prev, ...getFieldErrors(error) }));
    },
  });

  const handleSubmit = () => {
    const validationErrors = validateWorkOrderCreateForm(values);

    setErrors(validationErrors);

    if (hasErrors(validationErrors)) return;

    createMutation.mutate();
  };

  const updateType = (value: string) => {
    setFieldValue("type", value as WorkOrderType);
    setFieldValue("fault_id", "");
    setFieldValue("schedule_id", "");
  };

  const updateEquipment = (value: string) => {
    setFieldValue("equipment_id", value);
    setFieldValue("fault_id", "");
    setFieldValue("schedule_id", "");
  };

  const updateFault = (value: string) => {
    setFieldValue("fault_id", value);
  };

  const updateSchedule = (value: string) => {
    setFieldValue("schedule_id", value);
  };

  const updateTitle = (value: string) => {
    setFieldValue("title", value);
  };

  const updateDescription = (value: string) => {
    setFieldValue("description", value);
  };

  const updatePriority = (value: string) => {
    setFieldValue("priority", value as WorkOrderPriority);
  };

  return (
    <FormModal
      title="Новая заявка на обслуживание"
      submitLabel="Создать заявку"
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={createMutation.isPending}
      errorMessage={
        createMutation.isError ? getErrorMessage(createMutation.error) : null
      }
    >
      <div className="form-modal-row">
        <Select
          label="Тип заявки"
          value={values.type}
          options={TYPE_OPTIONS}
          onChange={updateType}
          isDisabled={!permissions.canCreatePlannedWorkOrder || isSourceLocked}
          helperText={
            permissions.canCreatePlannedWorkOrder
              ? undefined
              : "Плановые заявки создаёт главный инженер"
          }
          isRequired
        />
        <Select
          label="Приоритет"
          value={values.priority}
          options={PRIORITY_OPTIONS}
          onChange={updatePriority}
          isRequired
        />
      </div>
      <EquipmentPicker
        label="Оборудование"
        value={values.equipment_id}
        onChange={updateEquipment}
        errorMessage={errors.equipment_id}
        isDisabled={Boolean(initial.equipmentId) || isSourceLocked}
        isRequired
      />
      {isRepair ? (
        <Select
          label="Неисправность"
          value={values.fault_id}
          options={faultOptions}
          onChange={updateFault}
          placeholder="Без привязки к неисправности"
          errorMessage={errors.fault_id}
          helperText="Показаны открытые неисправности выбранного оборудования"
          isDisabled={!values.equipment_id || isSourceLocked}
        />
      ) : (
        <Select
          label="График ТО"
          value={values.schedule_id}
          options={scheduleOptions}
          onChange={updateSchedule}
          placeholder="Выберите график"
          errorMessage={errors.schedule_id}
          helperText="Показаны активные графики без текущей заявки"
          isDisabled={!values.equipment_id || isSourceLocked}
          isRequired
        />
      )}
      <TextField
        label="Заголовок"
        value={values.title}
        onChange={updateTitle}
        errorMessage={errors.title}
        maxLength={WORK_ORDER_LIMITS.TITLE_MAX}
        isRequired
      />
      <TextArea
        label="Описание работ"
        value={values.description}
        onChange={updateDescription}
        errorMessage={errors.description}
        maxLength={WORK_ORDER_LIMITS.DESCRIPTION_MAX}
        isRequired
      />
    </FormModal>
  );
};

export default CreateWorkOrderModal;
