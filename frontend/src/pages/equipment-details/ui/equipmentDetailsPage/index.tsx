"use client";

import Tabs from "@shared/ui/tabs";
import Panel from "@shared/ui/panel";
import Button from "@shared/ui/button";
import Lozenge from "@shared/ui/lozenge";
import PageHeader from "@shared/ui/pageHeader";
import DetailsLayout from "@shared/ui/detailsLayout";
import QueryBoundary from "@shared/ui/queryBoundary";
import SectionMessage from "@shared/ui/sectionMessage";
import DescriptionList from "@shared/ui/descriptionList";
import { ArchiveEquipmentModal } from "@features/equipment-management";
import { PlanFormModal } from "@features/maintenance-plan-management";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { EquipmentFormModal } from "@features/equipment-management";
import { CreateWorkOrderModal } from "@features/work-order-create";
import { IMaintenancePlan } from "@entities/maintenance-plan";
import { EquipmentStatusLozenge } from "@entities/equipment";
import { FaultFormModal } from "@features/fault-management";
import { buildMaintenancePlanRoute } from "@shared/config";
import { WorkOrderTable } from "@widgets/work-order-table";
import { isEquipmentArchived } from "@entities/equipment";
import { useEquipmentQuery } from "@entities/equipment";
import { ScheduleTable } from "@widgets/schedule-table";
import { LozengeAppearance } from "@shared/ui/lozenge";
import { useViewerPermissions } from "@entities/user";
import { HistoryTable } from "@widgets/history-table";
import { buildWorkOrderRoute } from "@shared/config";
import { ButtonAppearance } from "@shared/ui/button";
import { buildTabPanelId } from "@shared/ui/tabs";
import { FaultTable } from "@widgets/fault-table";
import { formatDateTime } from "@shared/lib/date";
import { IWorkOrder } from "@entities/work-order";
import { formatDate } from "@shared/lib/date";
import { useRouter } from "next/navigation";
import { IconName } from "@shared/ui/icon";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ROUTES } from "@shared/config";
import { ITab } from "@shared/ui/tabs";
import { ReactElement } from "react";
import { useState } from "react";

const enum EquipmentTab {
  WORK_ORDERS = "work-orders",
  FAULTS = "faults",
  SCHEDULES = "schedules",
  HISTORY = "history",
}

const enum EquipmentDialog {
  EDIT = "edit",
  ARCHIVE = "archive",
  FAULT = "fault",
  WORK_ORDER = "work-order",
  PLAN = "plan",
}

interface IEquipmentDetailsPageProps {
  equipmentId: string;
}

const ALLOWED_ROLES: UserRole[] = [
  UserRole.ENGINEER,
  UserRole.TECHNICIAN,
  UserRole.OPERATOR,
];

const EquipmentDetailsPage = ({
  equipmentId,
}: IEquipmentDetailsPageProps): ReactElement => {
  const router = useRouter();
  const permissions = useViewerPermissions();
  const [selectedTab, setSelectedTab] = useState<string>(
    EquipmentTab.WORK_ORDERS
  );
  const [openedDialog, setOpenedDialog] = useState<EquipmentDialog | null>(
    null
  );
  const {
    data: equipment,
    isLoading,
    error,
    refetch,
  } = useEquipmentQuery(equipmentId);

  const tabs: ITab[] = [
    { id: EquipmentTab.WORK_ORDERS, label: "Заявки" },
    { id: EquipmentTab.FAULTS, label: "Неисправности" },
    ...(permissions.canViewSchedules
      ? [{ id: EquipmentTab.SCHEDULES, label: "Графики ТО" }]
      : []),
    { id: EquipmentTab.HISTORY, label: "История работ" },
  ];

  const closeDialog = () => setOpenedDialog(null);
  const openEdit = () => setOpenedDialog(EquipmentDialog.EDIT);
  const openArchive = () => setOpenedDialog(EquipmentDialog.ARCHIVE);
  const openFault = () => setOpenedDialog(EquipmentDialog.FAULT);
  const openWorkOrder = () => setOpenedDialog(EquipmentDialog.WORK_ORDER);
  const openPlan = () => setOpenedDialog(EquipmentDialog.PLAN);

  const handleRetry = () => {
    refetch();
  };

  const handleWorkOrderCreated = (workOrder: IWorkOrder) => {
    router.push(buildWorkOrderRoute(workOrder.id));
  };

  const handlePlanCreated = (plan: IMaintenancePlan) => {
    router.push(buildMaintenancePlanRoute(plan.id));
  };

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <QueryBoundary isLoading={isLoading} error={error} onRetry={handleRetry}>
        {equipment && (
          <>
            <PageHeader
              breadcrumbs={[{ label: "Оборудование", href: ROUTES.EQUIPMENT }]}
              title={
                <>
                  <span>{equipment.name}</span>
                  {isEquipmentArchived(equipment) ? (
                    <Lozenge
                      label="В архиве"
                      appearance={LozengeAppearance.DEFAULT}
                      isBold
                    />
                  ) : (
                    <EquipmentStatusLozenge status={equipment.status} />
                  )}
                </>
              }
              actions={
                <>
                  {!isEquipmentArchived(equipment) &&
                    permissions.canCreateWorkOrder && (
                      <Button
                        label="Создать заявку"
                        appearance={ButtonAppearance.PRIMARY}
                        iconBefore={IconName.ADD}
                        onClick={openWorkOrder}
                      />
                    )}
                  {!isEquipmentArchived(equipment) &&
                    permissions.canCreateFault && (
                      <Button
                        label="Зарегистрировать неисправность"
                        iconBefore={IconName.FAULT}
                        onClick={openFault}
                      />
                    )}
                  {!isEquipmentArchived(equipment) &&
                    permissions.canManagePlans && (
                      <Button
                        label="Создать регламент"
                        iconBefore={IconName.PLAN}
                        onClick={openPlan}
                      />
                    )}
                  {!isEquipmentArchived(equipment) &&
                    permissions.canManageEquipment && (
                      <Button
                        label="Изменить"
                        iconBefore={IconName.EDIT}
                        onClick={openEdit}
                      />
                    )}
                  {permissions.canManageEquipment && (
                    <Button
                      label={
                        isEquipmentArchived(equipment)
                          ? "Восстановить"
                          : "В архив"
                      }
                      appearance={ButtonAppearance.SUBTLE}
                      iconBefore={
                        isEquipmentArchived(equipment)
                          ? IconName.RESTORE
                          : IconName.ARCHIVE
                      }
                      onClick={openArchive}
                    />
                  )}
                </>
              }
            />
            <DetailsLayout
              main={
                <>
                  {isEquipmentArchived(equipment) && (
                    <SectionMessage
                      appearance={SectionMessageAppearance.INFORMATION}
                      title="Оборудование в архиве"
                    >
                      <p>
                        Новые заявки и графики ТО недоступны. История
                        обслуживания сохранена и доступна ниже.
                      </p>
                    </SectionMessage>
                  )}
                  <div>
                    <Tabs
                      label="Разделы карточки оборудования"
                      tabs={tabs}
                      selectedId={selectedTab}
                      onChange={setSelectedTab}
                    />
                    <div
                      role="tabpanel"
                      id={buildTabPanelId(selectedTab)}
                      aria-labelledby={`tab-${selectedTab}`}
                    >
                      {selectedTab === EquipmentTab.WORK_ORDERS && (
                        <WorkOrderTable
                          fixedFilters={{ equipment_id: equipment.id }}
                        />
                      )}
                      {selectedTab === EquipmentTab.FAULTS && (
                        <FaultTable
                          fixedFilters={{ equipment_id: equipment.id }}
                        />
                      )}
                      {selectedTab === EquipmentTab.SCHEDULES && (
                        <ScheduleTable
                          fixedFilters={{ equipment_id: equipment.id }}
                        />
                      )}
                      {selectedTab === EquipmentTab.HISTORY && (
                        <HistoryTable
                          fixedFilters={{ equipment_id: equipment.id }}
                        />
                      )}
                    </div>
                  </div>
                </>
              }
              side={
                <Panel title="Карточка">
                  <DescriptionList
                    items={[
                      {
                        label: "Инвентарный номер",
                        value: (
                          <span className="code-text">
                            {equipment.inventory_number}
                          </span>
                        ),
                      },
                      { label: "Категория", value: equipment.category },
                      {
                        label: "Цех / местоположение",
                        value: equipment.location,
                      },
                      {
                        label: "Ввод в эксплуатацию",
                        value: formatDate(equipment.commissioned_on),
                      },
                      {
                        label: "Статус",
                        value: (
                          <EquipmentStatusLozenge status={equipment.status} />
                        ),
                      },
                      {
                        label: "В архиве с",
                        value: equipment.archived_at
                          ? formatDateTime(equipment.archived_at)
                          : null,
                      },
                      {
                        label: "Создана",
                        value: formatDateTime(equipment.created_at),
                      },
                      {
                        label: "Изменена",
                        value: formatDateTime(equipment.updated_at),
                      },
                    ]}
                  />
                </Panel>
              }
            />
            {openedDialog === EquipmentDialog.EDIT && (
              <EquipmentFormModal equipment={equipment} onClose={closeDialog} />
            )}
            {openedDialog === EquipmentDialog.ARCHIVE && (
              <ArchiveEquipmentModal
                equipment={equipment}
                onClose={closeDialog}
              />
            )}
            {openedDialog === EquipmentDialog.FAULT && (
              <FaultFormModal
                equipmentId={equipment.id}
                onClose={closeDialog}
              />
            )}
            {openedDialog === EquipmentDialog.WORK_ORDER && (
              <CreateWorkOrderModal
                initial={{ equipmentId: equipment.id }}
                onClose={closeDialog}
                onCreated={handleWorkOrderCreated}
              />
            )}
            {openedDialog === EquipmentDialog.PLAN && (
              <PlanFormModal
                equipmentId={equipment.id}
                onClose={closeDialog}
                onSaved={handlePlanCreated}
              />
            )}
          </>
        )}
      </QueryBoundary>
    </RoleGate>
  );
};

export default EquipmentDetailsPage;
