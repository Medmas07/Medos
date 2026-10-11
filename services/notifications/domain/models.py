"""Notification domain models, enums, and value objects."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class NotificationCategory(str, Enum):
    ACCESS_GRANTED = "access_granted"
    NEW_RECORD = "new_record"
    DELEGATION_GRANTED = "delegation_granted"
    REQUEST_STATUS = "request_status"
    ALERT = "alert"
    REVIEW_REQUESTED = "review_requested"
    JOB_COMPLETED = "job_completed"


class RecipientRole(str, Enum):
    PATIENT = "patient"
    RELATIVE = "relative"
    CLINICIAN = "clinician"
    GOVERNANCE_REVIEWER = "governance_reviewer"
    HOSPITAL_ADMIN = "hospital_admin"
    RESEARCHER = "researcher"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Channel(str, Enum):
    IN_APP = "in_app"
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    # Accepted by the provider (for push, the push server); device receipt unconfirmed.
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


class ReceiptStatus(str, Enum):
    QUEUED = "queued"
    REJECTED = "rejected"


class OverallEventStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass(frozen=True)
class RelatedResource:
    resource_type: str
    resource_ref: str


@dataclass(frozen=True)
class AlertMetadata:
    advisory: bool = True
    requires_human_review: bool = True
    finding_type: str | None = None


@dataclass(frozen=True)
class NotificationPayload:
    notification_id: str
    recipient_ref: str
    recipient_role: RecipientRole
    category: NotificationCategory
    priority: Priority
    title: str
    body: str
    channels: list[Channel]
    related_resource: RelatedResource | None = None
    alert_metadata: AlertMetadata | None = None
    fictional: bool = True


@dataclass(frozen=True)
class NotificationEvent:
    event_id: str
    event_type: str
    occurred_at: datetime
    source: str
    schema_version: str
    payload: NotificationPayload
    correlation_id: str | None = None


@dataclass(frozen=True)
class ChannelDeliveryRecord:
    channel: Channel
    status: DeliveryStatus
    dispatched_at: datetime | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class NotificationEventReceipt:
    receipt_id: str
    event_id: str
    status: ReceiptStatus
    queued_at: datetime
    recipient_ref: str
    fictional: bool = True


@dataclass(frozen=True)
class NotificationEventStatus:
    event_id: str
    status: OverallEventStatus
    received_at: datetime
    deliveries: list[ChannelDeliveryRecord] = field(default_factory=list)
    fictional: bool = True


@dataclass(frozen=True)
class RecipientPreference:
    recipient_ref: str
    enabled_channels: list[Channel] = field(
        default_factory=lambda: [Channel.IN_APP, Channel.PUSH, Channel.EMAIL]
    )
    muted_categories: list[NotificationCategory] = field(default_factory=list)
