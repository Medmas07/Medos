"""PushGatewayPort over HTTP: Web Push (RFC 8030) to a UnifiedPush endpoint (HC-204).

The message is encrypted to the subscription's keys (RFC 8291) and POSTed to its
endpoint, a capability URL on the push server (for the demo, ntfy). Redirects are not
followed. No VAPID header is sent: the push servers allowed by configuration accept
unauthenticated Web Push.
"""

import httpx

from adapters.outbound.webpush_encryption import encrypt
from application.push import PushOutcome, PushResult
from domain.push import PushSubscription

# How long the push server keeps a message for an offline device, in seconds.
DEFAULT_TTL_SECONDS = 24 * 3600


class UnifiedPushGateway:
    def __init__(
        self,
        timeout_seconds: float = 10.0,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        transport=None,
    ) -> None:
        self._timeout = timeout_seconds
        self._ttl = ttl_seconds
        self._transport = transport

    def send(
        self, subscription: PushSubscription, message: bytes, urgency: str
    ) -> PushResult:
        body = encrypt(message, subscription.p256dh, subscription.auth)
        headers = {
            "Content-Encoding": "aes128gcm",
            "Content-Type": "application/octet-stream",
            "TTL": str(self._ttl),
            "Urgency": urgency,
        }
        try:
            with httpx.Client(
                timeout=self._timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = client.post(
                    subscription.endpoint, content=body, headers=headers
                )
        except httpx.HTTPError as error:
            return PushResult(
                PushOutcome.REJECTED, f"no answer: {type(error).__name__}"
            )
        if 200 <= response.status_code < 300:
            return PushResult(PushOutcome.ACCEPTED)
        if response.status_code == 404:
            return PushResult(PushOutcome.GONE)
        if response.status_code == 429:
            return PushResult(PushOutcome.RATE_LIMITED)
        return PushResult(PushOutcome.REJECTED, f"HTTP {response.status_code}")
