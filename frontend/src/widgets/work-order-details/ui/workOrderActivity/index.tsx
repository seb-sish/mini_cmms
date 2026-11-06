"use client";

import QueryBoundary from "@shared/ui/queryBoundary";
import { WORK_ORDER_STATUS_LABELS } from "@entities/work-order";
import { useWorkOrderEventsQuery } from "@entities/work-order";
import { WORK_ORDER_EVENT_LABELS } from "@entities/work-order";
import { WorkOrderEventType } from "@entities/work-order";
import { IWorkOrderEvent } from "@entities/work-order";
import { formatDateTime } from "@shared/lib/date";
import { UserName } from "@entities/user";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

interface IWorkOrderActivityProps {
  workOrderId: string;
}

const renderEventDetails = (event: IWorkOrderEvent): ReactNode => {
  if (
    event.event_type === WorkOrderEventType.ASSIGNED ||
    event.event_type === WorkOrderEventType.REASSIGNED
  ) {
    return (
      <span className="work-order-activity-detail">
        Исполнитель: <UserName userId={event.new_assignee_id} />
      </span>
    );
  }

  if (
    event.from_status &&
    event.to_status &&
    event.from_status !== event.to_status
  ) {
    return (
      <span className="work-order-activity-detail">
        {WORK_ORDER_STATUS_LABELS[event.from_status]} {"->"}{" "}
        {WORK_ORDER_STATUS_LABELS[event.to_status]}
      </span>
    );
  }

  return null;
};

const WorkOrderActivity = ({
  workOrderId,
}: IWorkOrderActivityProps): ReactElement => {
  const { data, isLoading, error, refetch } =
    useWorkOrderEventsQuery(workOrderId);

  const handleRetry = () => {
    refetch();
  };

  return (
    <QueryBoundary isLoading={isLoading} error={error} onRetry={handleRetry}>
      <ol className="work-order-activity">
        {data?.items.map((event) => (
          <li key={event.id} className="work-order-activity-item">
            <div className="work-order-activity-header">
              <UserName userId={event.actor_id} />
              <span>{WORK_ORDER_EVENT_LABELS[event.event_type]}</span>
              <time
                className="body-small text-subtlest"
                dateTime={event.occurred_at}
              >
                {formatDateTime(event.occurred_at)}
              </time>
            </div>
            {renderEventDetails(event)}
          </li>
        ))}
      </ol>
    </QueryBoundary>
  );
};

export default WorkOrderActivity;
