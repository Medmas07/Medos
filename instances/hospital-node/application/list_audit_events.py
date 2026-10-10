from application.audit_log import AuditLog
from domain.audit_event import AuditEvent, AuditQuery


def list_audit_events(query: AuditQuery, audit_log: AuditLog) -> tuple[AuditEvent, ...]:
    return audit_log.events(query)
