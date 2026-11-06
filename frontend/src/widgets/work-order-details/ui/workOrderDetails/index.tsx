"use client";

import Link from "next/link";
import Panel from "@shared/ui/panel";
import PageHeader from "@shared/ui/pageHeader";
import SchedulePlanName from "../schedulePlanName";
import DetailsLayout from "@shared/ui/detailsLayout";
import QueryBoundary from "@shared/ui/queryBoundary";
import WorkOrderActivity from "../workOrderActivity";
import SectionMessage from "@shared/ui/sectionMessage";
import DescriptionList from "@shared/ui/descriptionList";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { getWorkOrderActions } from "@features/work-order-actions";
import { WorkOrderActionsBar } from "@features/work-order-actions";
import { WorkOrderChecklist } from "@features/work-order-actions";
import { WorkOrderStatusTracker } from "@entities/work-order";
import { WorkOrderStatusLozenge } from "@entities/work-order";
import { WorkOrderPriorityLabel } from "@entities/work-order";
import { WORK_ORDER_TYPE_LABELS } from "@entities/work-order";
import { IDescriptionItem } from "@shared/ui/descriptionList";
import { ReplacedPartsList } from "@entities/work-history";
import { useWorkOrderQuery } from "@entities/work-order";
import { WorkOrderStatus } from "@entities/work-order";
import { WorkOrderType } from "@entities/work-order";
import { EquipmentName } from "@entities/equipment";
import { formatDateTime } from "@shared/lib/date";
import { IWorkOrder } from "@entities/work-order";
import { buildFaultRoute } from "@shared/config";
import { formatDate } from "@shared/lib/date";
import { useViewer } from "@entities/user";
import { UserName } from "@entities/user";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";
import "./style.css";

interface IWorkOrderDetailsProps {
  workOrderId: string;
}

const buildDetailItems = (workOrder: IWorkOrder): IDescriptionItem[] => [
  {
    label: "Статус",
    value: <WorkOrderStatusLozenge status={workOrder.status} isBold />,
  },
  { label: "Тип", value: WORK_ORDER_TYPE_LABELS[workOrder.type] },
  {
    label: "Приоритет",
    value: <WorkOrderPriorityLabel priority={workOrder.priority} />,
  },
  {
    label: "Оборудование",
    value: <EquipmentName equipmentId={workOrder.equipment_id} />,
  },
  ...(workOrder.fault_id
    ? [
        {
          label: "Неисправность",
          value: (
            <Link href={buildFaultRoute(workOrder.fault_id)}>
              Открыть неисправность
            </Link>
          ),
        },
      ]
    : []),
  ...(workOrder.schedule_id
    ? [
        {
          label: "Регламент",
          value: <SchedulePlanName scheduleId={workOrder.schedule_id} />,
        },
        {
          label: "Плановый срок",
          value: workOrder.planned_due_on
            ? formatDate(workOrder.planned_due_on)
            : null,
        },
      ]
    : []),
  { label: "Исполнитель", value: <UserName userId={workOrder.assignee_id} /> },
  { label: "Автор", value: <UserName userId={workOrder.author_id} /> },
  { label: "Создана", value: formatDateTime(workOrder.created_at) },
  {
    label: "Выполнена",
    value: workOrder.completed_at
      ? formatDateTime(workOrder.completed_at)
      : null,
  },
  {
    label: "Закрыта",
    value: workOrder.closed_at ? formatDateTime(workOrder.closed_at) : null,
  },
];

const WorkOrderDetails = ({
  workOrderId,
}: IWorkOrderDetailsProps): ReactElement => {
  const viewer = useViewer();
  const {
    data: workOrder,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useWorkOrderQuery(workOrderId);

  const handleRetry = () => {
    refetch();
  };

  return (
    <QueryBoundary isLoading={isLoading} error={error} onRetry={handleRetry}>
      {workOrder && (
        <div className="work-order-details">
          <PageHeader
            breadcrumbs={[{ label: "Заявки", href: ROUTES.WORK_ORDERS }]}
            title={
              <>
                <span className="work-order-details-number code-text">
                  {workOrder.number}
                </span>
                <span>{workOrder.title}</span>
              </>
            }
            actions={<WorkOrderActionsBar workOrder={workOrder} />}
          />
          <div className="work-order-details-tracker">
            <WorkOrderStatusTracker status={workOrder.status} />
          </div>
          <DetailsLayout
            main={
              <>
                {workOrder.status === WorkOrderStatus.CANCELLED && (
                  <SectionMessage
                    appearance={SectionMessageAppearance.WARNING}
                    title="Заявка отменена"
                  >
                    <p className="pre-wrap-text">
                      Причина: {workOrder.cancellation_reason}
                    </p>
                    {workOrder.cancelled_at && (
                      <p className="body-small">
                        {formatDateTime(workOrder.cancelled_at)},{" "}
                        <UserName userId={workOrder.cancelled_by} />
                      </p>
                    )}
                  </SectionMessage>
                )}
                <Panel title="Описание">
                  <p className="pre-wrap-text">{workOrder.description}</p>
                </Panel>
                {workOrder.type === WorkOrderType.PLANNED && (
                  <Panel title="Чек-лист операций">
                    {workOrder.checklist.length > 0 ? (
                      <WorkOrderChecklist
                        workOrder={workOrder}
                        isEditable={
                          getWorkOrderActions(viewer, workOrder)
                            .canUpdateChecklist
                        }
                        isRefreshing={isFetching}
                      />
                    ) : (
                      <p className="text-subtlest">Чек-лист регламента пуст.</p>
                    )}
                  </Panel>
                )}
                {workOrder.result && (
                  <Panel title="Результат работ">
                    <p className="pre-wrap-text">{workOrder.result}</p>
                    <div>
                      <h3 className="heading-xsmall">Заменённые детали</h3>
                      <ReplacedPartsList parts={workOrder.replaced_parts} />
                    </div>
                  </Panel>
                )}
                <Panel title="Журнал событий">
                  <WorkOrderActivity workOrderId={workOrder.id} />
                </Panel>
              </>
            }
            side={
              <Panel title="Сведения">
                <DescriptionList items={buildDetailItems(workOrder)} />
              </Panel>
            }
          />
        </div>
      )}
    </QueryBoundary>
  );
};

export default WorkOrderDetails;
