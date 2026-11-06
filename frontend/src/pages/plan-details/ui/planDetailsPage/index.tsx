"use client";

import Panel from "@shared/ui/panel";
import Button from "@shared/ui/button";
import Lozenge from "@shared/ui/lozenge";
import PageHeader from "@shared/ui/pageHeader";
import DetailsLayout from "@shared/ui/detailsLayout";
import QueryBoundary from "@shared/ui/queryBoundary";
import DescriptionList from "@shared/ui/descriptionList";
import { TogglePlanModal } from "@features/maintenance-plan-management";
import { PlanFormModal } from "@features/maintenance-plan-management";
import { useMaintenancePlanQuery } from "@entities/maintenance-plan";
import { PlanEnabledLozenge } from "@entities/maintenance-plan";
import { PLAN_SCOPE_LABELS } from "@entities/maintenance-plan";
import { formatInterval } from "@entities/maintenance-plan";
import { ScheduleTable } from "@widgets/schedule-table";
import { LozengeAppearance } from "@shared/ui/lozenge";
import { PlanScope } from "@entities/maintenance-plan";
import { useViewerPermissions } from "@entities/user";
import { ButtonAppearance } from "@shared/ui/button";
import { EquipmentName } from "@entities/equipment";
import { formatDateTime } from "@shared/lib/date";
import { formatDate } from "@shared/lib/date";
import { IconName } from "@shared/ui/icon";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";
import { useState } from "react";
import "./style.css";

const enum PlanDialog {
  EDIT = "edit",
  TOGGLE = "toggle",
}

interface IPlanDetailsPageProps {
  planId: string;
}

const ALLOWED_ROLES: UserRole[] = [UserRole.ENGINEER, UserRole.TECHNICIAN];

const PlanDetailsPage = ({ planId }: IPlanDetailsPageProps): ReactElement => {
  const permissions = useViewerPermissions();
  const [openedDialog, setOpenedDialog] = useState<PlanDialog | null>(null);
  const {
    data: plan,
    isLoading,
    error,
    refetch,
  } = useMaintenancePlanQuery(planId);

  const closeDialog = () => setOpenedDialog(null);
  const openEdit = () => setOpenedDialog(PlanDialog.EDIT);
  const openToggle = () => setOpenedDialog(PlanDialog.TOGGLE);

  const handleRetry = () => {
    refetch();
  };

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <QueryBoundary isLoading={isLoading} error={error} onRetry={handleRetry}>
        {plan && (
          <>
            <PageHeader
              breadcrumbs={[
                { label: "Регламенты ТО", href: ROUTES.MAINTENANCE_PLANS },
              ]}
              title={
                <>
                  <span>{plan.name}</span>
                  <PlanEnabledLozenge isEnabled={plan.enabled} />
                </>
              }
              actions={
                permissions.canManagePlans && (
                  <>
                    <Button
                      label="Изменить"
                      iconBefore={IconName.EDIT}
                      onClick={openEdit}
                    />
                    <Button
                      label={plan.enabled ? "Приостановить" : "Возобновить"}
                      appearance={ButtonAppearance.SUBTLE}
                      iconBefore={
                        plan.enabled ? IconName.LOCK : IconName.UNLOCK
                      }
                      onClick={openToggle}
                    />
                  </>
                )
              }
            />
            <DetailsLayout
              main={
                <>
                  <Panel title="Чек-лист операций">
                    <ol className="plan-details-checklist">
                      {[...plan.checklist]
                        .sort((left, right) => left.order - right.order)
                        .map((item) => (
                          <li key={item.id}>
                            <span>{item.title}</span>
                            {item.required ? (
                              <Lozenge
                                label="Обязательно"
                                appearance={LozengeAppearance.REMOVED}
                              />
                            ) : (
                              <Lozenge label="По необходимости" />
                            )}
                          </li>
                        ))}
                    </ol>
                  </Panel>
                  <Panel title="Графики ТО по оборудованию">
                    <ScheduleTable fixedFilters={{ plan_id: plan.id }} />
                  </Panel>
                </>
              }
              side={
                <Panel title="Параметры">
                  <DescriptionList
                    items={[
                      {
                        label: "Область",
                        value: PLAN_SCOPE_LABELS[plan.scope],
                      },
                      plan.scope === PlanScope.EQUIPMENT && plan.equipment_id
                        ? {
                            label: "Оборудование",
                            value: (
                              <EquipmentName equipmentId={plan.equipment_id} />
                            ),
                          }
                        : { label: "Категория", value: plan.category },
                      {
                        label: "Периодичность",
                        value: formatInterval(plan.interval_days),
                      },
                      {
                        label: "Первый срок",
                        value: formatDate(plan.first_due_on),
                      },
                      {
                        label: "Состояние",
                        value: <PlanEnabledLozenge isEnabled={plan.enabled} />,
                      },
                      {
                        label: "Создан",
                        value: formatDateTime(plan.created_at),
                      },
                      {
                        label: "Изменён",
                        value: formatDateTime(plan.updated_at),
                      },
                    ]}
                  />
                </Panel>
              }
            />
            {openedDialog === PlanDialog.EDIT && (
              <PlanFormModal plan={plan} onClose={closeDialog} />
            )}
            {openedDialog === PlanDialog.TOGGLE && (
              <TogglePlanModal plan={plan} onClose={closeDialog} />
            )}
          </>
        )}
      </QueryBoundary>
    </RoleGate>
  );
};

export default PlanDetailsPage;
