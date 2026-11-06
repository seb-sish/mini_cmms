"use client";

import Panel from "@shared/ui/panel";
import Button from "@shared/ui/button";
import PageHeader from "@shared/ui/pageHeader";
import LinkButton from "@shared/ui/linkButton";
import { CreateWorkOrderModal } from "@features/work-order-create";
import { NotificationList } from "@widgets/notification-list";
import { FaultFormModal } from "@features/fault-management";
import { WorkOrderTable } from "@widgets/work-order-table";
import { ScheduleTable } from "@widgets/schedule-table";
import { WorkOrderStatus } from "@entities/work-order";
import { useViewerPermissions } from "@entities/user";
import { buildWorkOrderRoute } from "@shared/config";
import { ButtonAppearance } from "@shared/ui/button";
import { USER_ROLE_LABELS } from "@entities/user";
import { FaultTable } from "@widgets/fault-table";
import { IWorkOrder } from "@entities/work-order";
import { useRouter } from "next/navigation";
import { IconName } from "@shared/ui/icon";
import { useViewer } from "@entities/user";
import { UserRole } from "@entities/user";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";
import { useEffect } from "react";
import { useState } from "react";
import "./style.css";

const DASHBOARD_PAGE_SIZE = 5;

const HomePage = (): ReactElement => {
  const router = useRouter();
  const viewer = useViewer();
  const permissions = useViewerPermissions();
  const [isWorkOrderModalOpen, setIsWorkOrderModalOpen] =
    useState<boolean>(false);
  const [isFaultModalOpen, setIsFaultModalOpen] = useState<boolean>(false);

  useEffect(() => {
    if (viewer.role === UserRole.ADMIN) router.replace(ROUTES.USERS);
  }, [viewer.role, router]);

  const openWorkOrderModal = () => setIsWorkOrderModalOpen(true);
  const closeWorkOrderModal = () => setIsWorkOrderModalOpen(false);
  const openFaultModal = () => setIsFaultModalOpen(true);
  const closeFaultModal = () => setIsFaultModalOpen(false);

  const handleWorkOrderCreated = (workOrder: IWorkOrder) => {
    router.push(buildWorkOrderRoute(workOrder.id));
  };

  return (
    <div className="home-page">
      <PageHeader
        title={`Добро пожаловать, ${viewer.login}`}
        actions={
          <>
            {permissions.canCreateFault && (
              <Button
                label="Зарегистрировать неисправность"
                iconBefore={IconName.FAULT}
                onClick={openFaultModal}
              />
            )}
            {permissions.canCreateWorkOrder && (
              <Button
                label="Создать заявку"
                appearance={ButtonAppearance.PRIMARY}
                iconBefore={IconName.ADD}
                onClick={openWorkOrderModal}
              />
            )}
          </>
        }
      />
      <p className="home-page-role text-subtle">
        Роль: {USER_ROLE_LABELS[viewer.role]}
      </p>
      {viewer.role === UserRole.ENGINEER && (
        <div className="home-page-grid">
          <Panel
            title="Просроченное ТО"
            actions={<LinkButton label="Весь график" href={ROUTES.SCHEDULES} />}
          >
            <ScheduleTable
              initialOverdue
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
            />
          </Panel>
          <Panel title="Ожидают назначения исполнителя">
            <WorkOrderTable
              fixedFilters={{ status: WorkOrderStatus.CREATED }}
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
              emptyTitle="Все заявки распределены"
            />
          </Panel>
          <Panel title="Ожидают приёмки">
            <WorkOrderTable
              fixedFilters={{ status: WorkOrderStatus.COMPLETED }}
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
              emptyTitle="Нет выполненных заявок для приёмки"
            />
          </Panel>
          <Panel
            title="Последние напоминания"
            actions={
              <LinkButton label="Все уведомления" href={ROUTES.NOTIFICATIONS} />
            }
          >
            <NotificationList
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
            />
          </Panel>
        </div>
      )}
      {viewer.role === UserRole.TECHNICIAN && (
        <div className="home-page-grid">
          <Panel title="В работе">
            <WorkOrderTable
              fixedFilters={{ status: WorkOrderStatus.IN_PROGRESS }}
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
              emptyTitle="Нет заявок в работе"
            />
          </Panel>
          <Panel title="Назначены мне">
            <WorkOrderTable
              fixedFilters={{ status: WorkOrderStatus.ASSIGNED }}
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
              emptyTitle="Новых назначений нет"
            />
          </Panel>
          <Panel
            title="Ближайшее ТО"
            actions={<LinkButton label="Весь график" href={ROUTES.SCHEDULES} />}
          >
            <ScheduleTable
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
            />
          </Panel>
          <Panel
            title="Последние напоминания"
            actions={
              <LinkButton label="Все уведомления" href={ROUTES.NOTIFICATIONS} />
            }
          >
            <NotificationList
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
            />
          </Panel>
        </div>
      )}
      {viewer.role === UserRole.OPERATOR && (
        <div className="home-page-grid">
          <Panel
            title="Мои заявки"
            actions={
              <LinkButton label="Все заявки" href={ROUTES.WORK_ORDERS} />
            }
          >
            <WorkOrderTable
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
              emptyTitle="Вы ещё не создавали заявок"
            />
          </Panel>
          <Panel
            title="Мои неисправности"
            actions={<LinkButton label="Журнал" href={ROUTES.FAULTS} />}
          >
            <FaultTable
              fixedFilters={{ author_id: viewer.id }}
              isFilterable={false}
              pageSize={DASHBOARD_PAGE_SIZE}
            />
          </Panel>
        </div>
      )}
      {isWorkOrderModalOpen && (
        <CreateWorkOrderModal
          onClose={closeWorkOrderModal}
          onCreated={handleWorkOrderCreated}
        />
      )}
      {isFaultModalOpen && <FaultFormModal onClose={closeFaultModal} />}
    </div>
  );
};

export default HomePage;
