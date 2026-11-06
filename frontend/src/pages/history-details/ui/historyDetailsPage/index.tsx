"use client";

import Link from "next/link";
import Panel from "@shared/ui/panel";
import Lozenge from "@shared/ui/lozenge";
import PageHeader from "@shared/ui/pageHeader";
import DetailsLayout from "@shared/ui/detailsLayout";
import QueryBoundary from "@shared/ui/queryBoundary";
import DescriptionList from "@shared/ui/descriptionList";
import { useWorkHistoryQuery } from "@entities/work-history";
import { ReplacedPartsList } from "@entities/work-history";
import { LozengeAppearance } from "@shared/ui/lozenge";
import { PlanName } from "@entities/maintenance-plan";
import { buildWorkOrderRoute } from "@shared/config";
import { EquipmentName } from "@entities/equipment";
import { formatDateTime } from "@shared/lib/date";
import { buildFaultRoute } from "@shared/config";
import { RoleGate } from "@entities/user";
import { UserName } from "@entities/user";
import { UserRole } from "@entities/user";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";

interface IHistoryDetailsPageProps {
  historyId: string;
}

const ALLOWED_ROLES: UserRole[] = [
  UserRole.ENGINEER,
  UserRole.TECHNICIAN,
  UserRole.OPERATOR,
];

const HistoryDetailsPage = ({
  historyId,
}: IHistoryDetailsPageProps): ReactElement => {
  const {
    data: history,
    isLoading,
    error,
    refetch,
  } = useWorkHistoryQuery(historyId);

  const handleRetry = () => {
    refetch();
  };

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <QueryBoundary isLoading={isLoading} error={error} onRetry={handleRetry}>
        {history && (
          <>
            <PageHeader
              breadcrumbs={[{ label: "История работ", href: ROUTES.HISTORY }]}
              title={
                <>
                  <span>Работа от {formatDateTime(history.completed_at)}</span>
                  <Lozenge
                    label="Закрыта"
                    appearance={LozengeAppearance.SUCCESS}
                  />
                </>
              }
            />
            <DetailsLayout
              main={
                <>
                  <Panel title="Результат работ">
                    <p className="pre-wrap-text">{history.result}</p>
                  </Panel>
                  <Panel title="Заменённые детали">
                    <ReplacedPartsList parts={history.replaced_parts} />
                  </Panel>
                  <p className="body-small text-subtlest">
                    Запись истории неизменяема и сохраняется при архивировании
                    оборудования или блокировке исполнителя.
                  </p>
                </>
              }
              side={
                <Panel title="Сведения">
                  <DescriptionList
                    items={[
                      {
                        label: "Оборудование",
                        value: (
                          <EquipmentName equipmentId={history.equipment_id} />
                        ),
                      },
                      {
                        label: "Вид работ",
                        value: history.plan_id ? "Плановое ТО" : "Ремонт",
                      },
                      {
                        label: "Заявка",
                        value: (
                          <Link
                            href={buildWorkOrderRoute(history.work_order_id)}
                          >
                            Открыть заявку
                          </Link>
                        ),
                      },
                      {
                        label: "Регламент",
                        value: history.plan_id ? (
                          <PlanName planId={history.plan_id} />
                        ) : null,
                      },
                      {
                        label: "Неисправность",
                        value: history.fault_id ? (
                          <Link href={buildFaultRoute(history.fault_id)}>
                            Открыть неисправность
                          </Link>
                        ) : null,
                      },
                      {
                        label: "Исполнитель",
                        value: <UserName userId={history.technician_id} />,
                      },
                      {
                        label: "Выполнено",
                        value: formatDateTime(history.completed_at),
                      },
                      {
                        label: "Принято",
                        value: formatDateTime(history.closed_at),
                      },
                    ]}
                  />
                </Panel>
              }
            />
          </>
        )}
      </QueryBoundary>
    </RoleGate>
  );
};

export default HistoryDetailsPage;
