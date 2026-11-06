"use client";

import Panel from "@shared/ui/panel";
import Button from "@shared/ui/button";
import PageHeader from "@shared/ui/pageHeader";
import DetailsLayout from "@shared/ui/detailsLayout";
import QueryBoundary from "@shared/ui/queryBoundary";
import DescriptionList from "@shared/ui/descriptionList";
import { CreateWorkOrderModal } from "@features/work-order-create";
import { FaultFormModal } from "@features/fault-management";
import { WorkOrderTable } from "@widgets/work-order-table";
import { canEditFault } from "@features/fault-management";
import { FaultSeverityLozenge } from "@entities/fault";
import { useViewerPermissions } from "@entities/user";
import { buildWorkOrderRoute } from "@shared/config";
import { FaultStatusLozenge } from "@entities/fault";
import { ButtonAppearance } from "@shared/ui/button";
import { WorkOrderType } from "@entities/work-order";
import { EquipmentName } from "@entities/equipment";
import { formatDateTime } from "@shared/lib/date";
import { IWorkOrder } from "@entities/work-order";
import { useFaultQuery } from "@entities/fault";
import { FaultStatus } from "@entities/fault";
import { formatDate } from "@shared/lib/date";
import { useRouter } from "next/navigation";
import { IconName } from "@shared/ui/icon";
import { useViewer } from "@entities/user";
import { RoleGate } from "@entities/user";
import { UserName } from "@entities/user";
import { UserRole } from "@entities/user";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";
import { useState } from "react";

const enum FaultDialog {
  EDIT = "edit",
  WORK_ORDER = "work-order",
}

interface IFaultDetailsPageProps {
  faultId: string;
}

const ALLOWED_ROLES: UserRole[] = [
  UserRole.ENGINEER,
  UserRole.TECHNICIAN,
  UserRole.OPERATOR,
];

const FaultDetailsPage = ({
  faultId,
}: IFaultDetailsPageProps): ReactElement => {
  const router = useRouter();
  const viewer = useViewer();
  const permissions = useViewerPermissions();
  const [openedDialog, setOpenedDialog] = useState<FaultDialog | null>(null);
  const { data: fault, isLoading, error, refetch } = useFaultQuery(faultId);

  const closeDialog = () => setOpenedDialog(null);
  const openEdit = () => setOpenedDialog(FaultDialog.EDIT);
  const openWorkOrder = () => setOpenedDialog(FaultDialog.WORK_ORDER);

  const handleRetry = () => {
    refetch();
  };

  const handleWorkOrderCreated = (workOrder: IWorkOrder) => {
    router.push(buildWorkOrderRoute(workOrder.id));
  };

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <QueryBoundary isLoading={isLoading} error={error} onRetry={handleRetry}>
        {fault && (
          <>
            <PageHeader
              breadcrumbs={[
                { label: "Журнал неисправностей", href: ROUTES.FAULTS },
              ]}
              title={
                <>
                  <span>Неисправность от {formatDate(fault.detected_on)}</span>
                  <FaultStatusLozenge status={fault.status} />
                </>
              }
              actions={
                <>
                  {fault.status === FaultStatus.OPEN &&
                    permissions.canCreateWorkOrder && (
                      <Button
                        label="Создать заявку на ремонт"
                        appearance={ButtonAppearance.PRIMARY}
                        iconBefore={IconName.ADD}
                        onClick={openWorkOrder}
                      />
                    )}
                  {canEditFault(viewer, fault) && (
                    <Button
                      label="Изменить"
                      iconBefore={IconName.EDIT}
                      onClick={openEdit}
                    />
                  )}
                </>
              }
            />
            <DetailsLayout
              main={
                <>
                  <Panel title="Описание">
                    <p className="pre-wrap-text">{fault.description}</p>
                  </Panel>
                  <Panel title="Заявки на устранение">
                    <WorkOrderTable
                      fixedFilters={{ fault_id: fault.id }}
                      isFilterable={false}
                      emptyTitle="Заявок по этой неисправности ещё нет"
                    />
                  </Panel>
                </>
              }
              side={
                <Panel title="Сведения">
                  <DescriptionList
                    items={[
                      {
                        label: "Оборудование",
                        value: (
                          <EquipmentName equipmentId={fault.equipment_id} />
                        ),
                      },
                      {
                        label: "Статус",
                        value: <FaultStatusLozenge status={fault.status} />,
                      },
                      {
                        label: "Критичность",
                        value: (
                          <FaultSeverityLozenge severity={fault.severity} />
                        ),
                      },
                      {
                        label: "Дата обнаружения",
                        value: formatDate(fault.detected_on),
                      },
                      {
                        label: "Автор",
                        value: <UserName userId={fault.author_id} />,
                      },
                      {
                        label: "Зарегистрирована",
                        value: formatDateTime(fault.created_at),
                      },
                      {
                        label: "Изменена",
                        value: formatDateTime(fault.updated_at),
                      },
                    ]}
                  />
                  <p className="body-small text-subtlest">
                    Статус неисправности меняется автоматически: &quot;В
                    работе&quot; при начале ремонта, &quot;Устранена&quot; при
                    закрытии заявки.
                  </p>
                </Panel>
              }
            />
            {openedDialog === FaultDialog.EDIT && (
              <FaultFormModal fault={fault} onClose={closeDialog} />
            )}
            {openedDialog === FaultDialog.WORK_ORDER && (
              <CreateWorkOrderModal
                initial={{
                  type: WorkOrderType.REPAIR,
                  equipmentId: fault.equipment_id,
                  faultId: fault.id,
                }}
                onClose={closeDialog}
                onCreated={handleWorkOrderCreated}
              />
            )}
          </>
        )}
      </QueryBoundary>
    </RoleGate>
  );
};

export default FaultDetailsPage;
