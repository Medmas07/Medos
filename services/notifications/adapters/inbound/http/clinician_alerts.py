"""HC-203: Real-time clinician alert HTTP endpoints.

Provides:
  GET /v1/clinicians/{clinician_ref}/alerts
      Returns advisory alert-category notifications for the given clinician,
      ordered by priority then recency.

  GET /v1/clinicians/{clinician_ref}/alerts/stream
      Server-Sent Events (SSE) stream that emits the current alert list once
      and then pushes incremental refreshes every `interval` seconds.
      D3 boundary: polling-based SSE emulation; no real push broker at this depth.
      The stream is explicitly labelled as MOCKED real-time and not presented as
      production WebSocket or broker-backed delivery.

All alert payloads carry advisory=true and requires_human_review=true.
No raw clinical data, diagnosis, or prescription authority is exposed.
"""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from application.use_cases import ListClinicianAlertsUseCase
from adapters.inbound.http.problems import problem_response


def _alert_to_dict(event: Any) -> dict:
    """Serialize a clinician NotificationEvent to a wire-safe dict."""
    p = event.payload
    return {
        "event_id": event.event_id,
        "notification_id": p.notification_id,
        "priority": p.priority.value,
        "title": p.title,
        "body": p.body,
        "occurred_at": event.occurred_at.isoformat(),
        "source": event.source,
        "alert_metadata": {
            "advisory": p.alert_metadata.advisory if p.alert_metadata else True,
            "requires_human_review": (
                p.alert_metadata.requires_human_review if p.alert_metadata else True
            ),
            "finding_type": p.alert_metadata.finding_type if p.alert_metadata else None,
        },
        "related_resource": {
            "resource_type": p.related_resource.resource_type,
            "resource_ref": p.related_resource.resource_ref,
        }
        if p.related_resource
        else None,
        "fictional": p.fictional,
    }


def create_clinician_alerts_router(
    list_alerts_use_case: ListClinicianAlertsUseCase,
) -> APIRouter:
    router = APIRouter()

    @router.get("/v1/clinicians/{clinician_ref}/alerts")
    def list_clinician_alerts(clinician_ref: str) -> Any:
        """List advisory alert-category notifications for a clinician.

        HC-203 (D3). Results ordered by priority then recency.
        All alerts are advisory and require human clinician review.
        """
        alerts = list_alerts_use_case.execute(clinician_ref)
        return {
            "clinician_ref": clinician_ref,
            "count": len(alerts),
            "advisory_notice": (
                "All alerts are strictly advisory (D3). "
                "No clinical action should be taken based solely on this data. "
                "Clinician review is mandatory."
            ),
            "alerts": [_alert_to_dict(e) for e in alerts],
            "fictional": True,
        }

    @router.get("/v1/clinicians/{clinician_ref}/alerts/stream")
    async def stream_clinician_alerts(
        clinician_ref: str, request: Request, interval: int = 10
    ) -> StreamingResponse:
        """Server-Sent Events stream of clinician alerts.

        HC-203 (D3) — polling-based SSE emulation.
        Emits the current alert list as SSE events, then refreshes every
        `interval` seconds. This is a D3 simulation of real-time delivery;
        no broker, WebSocket, or persistent push subscription is established.
        Clearly labelled as MOCKED real-time for demo and review purposes.
        """
        interval = max(5, min(interval, 60))

        async def event_generator():
            # Initial advisory comment so the client knows the stream boundary
            yield (
                "event: stream_opened\n"
                'data: {"notice": "HC-203 D3 SSE simulation. '
                "Polling-based, not broker-backed. "
                'Advisory only — clinician review required.", "fictional": true}\n\n'
            )

            while True:
                if await request.is_disconnected():
                    break

                alerts = list_alerts_use_case.execute(clinician_ref)
                payload = json.dumps(
                    {
                        "clinician_ref": clinician_ref,
                        "count": len(alerts),
                        "alerts": [_alert_to_dict(e) for e in alerts],
                        "advisory_notice": (
                            "Strictly advisory. Clinician review required."
                        ),
                        "fictional": True,
                    },
                    ensure_ascii=False,
                )
                yield f"event: alerts_updated\ndata: {payload}\n\n"
                await asyncio.sleep(interval)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-HC-203-Boundary": "D3-SSE-simulation-polling-based",
            },
        )

    return router
