"""HTTP endpoints conforming to contracts/events/notification-event.v1.yaml."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from adapters.inbound.http.problems import problem_response
from application.use_cases import (
    GetNotificationEventStatusUseCase,
    IngestNotificationEventUseCase,
    ListRecipientNotificationsUseCase,
)
from domain.models import (
    AlertMetadata,
    Channel,
    NotificationCategory,
    NotificationEvent,
    NotificationPayload,
    Priority,
    RecipientRole,
    RelatedResource,
)
from domain.validation import DomainValidationError


class RelatedResourceDto(BaseModel):
    resource_type: str
    resource_ref: str


class AlertMetadataDto(BaseModel):
    advisory: bool
    requires_human_review: bool
    finding_type: str | None = None


class NotificationPayloadDto(BaseModel):
    notification_id: str
    recipient_ref: str
    recipient_role: RecipientRole
    category: NotificationCategory
    priority: Priority = Priority.NORMAL
    title: str = Field(..., max_length=120)
    body: str = Field(..., max_length=500)
    channels: list[Channel]
    related_resource: RelatedResourceDto | None = None
    alert_metadata: AlertMetadataDto | None = None
    fictional: bool = True


class NotificationEventEnvelopeDto(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime
    source: str
    schema_version: str = "1.0.0"
    correlation_id: str | None = None
    payload: NotificationPayloadDto


def create_router(
    ingest_use_case: IngestNotificationEventUseCase,
    get_status_use_case: GetNotificationEventStatusUseCase,
    list_recipient_use_case: ListRecipientNotificationsUseCase,
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/v1/events/notifications",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def publish_notification_event(
        body: NotificationEventEnvelopeDto, response: Response
    ) -> Any:
        try:
            payload = NotificationPayload(
                notification_id=body.payload.notification_id,
                recipient_ref=body.payload.recipient_ref,
                recipient_role=body.payload.recipient_role,
                category=body.payload.category,
                priority=body.payload.priority,
                title=body.payload.title,
                body=body.payload.body,
                channels=body.payload.channels,
                related_resource=RelatedResource(
                    resource_type=body.payload.related_resource.resource_type,
                    resource_ref=body.payload.related_resource.resource_ref,
                )
                if body.payload.related_resource
                else None,
                alert_metadata=AlertMetadata(
                    advisory=body.payload.alert_metadata.advisory,
                    requires_human_review=body.payload.alert_metadata.requires_human_review,
                    finding_type=body.payload.alert_metadata.finding_type,
                )
                if body.payload.alert_metadata
                else None,
                fictional=body.payload.fictional,
            )

            event = NotificationEvent(
                event_id=body.event_id,
                event_type=body.event_type,
                occurred_at=body.occurred_at,
                source=body.source,
                schema_version=body.schema_version,
                correlation_id=body.correlation_id,
                payload=payload,
            )

            receipt = ingest_use_case.execute(event)

            return {
                "receipt_id": receipt.receipt_id,
                "event_id": receipt.event_id,
                "status": receipt.status.value,
                "queued_at": receipt.queued_at.isoformat(),
                "recipient_ref": receipt.recipient_ref,
                "fictional": receipt.fictional,
            }
        except DomainValidationError as e:
            return problem_response(
                status=400,
                title="Invalid Notification Event",
                detail=str(e),
                type_uri="https://hackcure.org/errors/invalid-notification-event",
            )
        except Exception as e:
            return problem_response(
                status=400,
                title="Invalid Notification Event",
                detail=f"Failed to process event: {e}",
                type_uri="https://hackcure.org/errors/invalid-notification-event",
            )

    @router.get("/v1/events/notifications/{event_id}")
    def get_event_status(event_id: str) -> Any:
        event_status = get_status_use_case.execute(event_id)
        if not event_status:
            return problem_response(
                status=404,
                title="Event Not Found",
                detail=f"No notification event found matching ID '{event_id}'.",
                type_uri="https://hackcure.org/errors/event-not-found",
            )

        return {
            "event_id": event_status.event_id,
            "status": event_status.status.value,
            "received_at": event_status.received_at.isoformat(),
            "deliveries": [
                {
                    "channel": d.channel.value,
                    "status": d.status.value,
                    "dispatched_at": d.dispatched_at.isoformat()
                    if d.dispatched_at
                    else None,
                    "failure_reason": d.failure_reason,
                }
                for d in event_status.deliveries
            ],
            "fictional": event_status.fictional,
        }

    @router.get("/v1/recipients/{recipient_ref}/notifications")
    def list_recipient_notifications(recipient_ref: str) -> Any:
        events = list_recipient_use_case.execute(recipient_ref)
        return {
            "recipient_ref": recipient_ref,
            "count": len(events),
            "notifications": [
                {
                    "event_id": e.event_id,
                    "notification_id": e.payload.notification_id,
                    "category": e.payload.category.value,
                    "priority": e.payload.priority.value,
                    "title": e.payload.title,
                    "body": e.payload.body,
                    "occurred_at": e.occurred_at.isoformat(),
                    "source": e.source,
                    "related_resource": {
                        "resource_type": e.payload.related_resource.resource_type,
                        "resource_ref": e.payload.related_resource.resource_ref,
                    }
                    if e.payload.related_resource
                    else None,
                    "fictional": e.payload.fictional,
                }
                for e in events
            ],
        }

    return router
