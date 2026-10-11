"""contracts/api/notifications/push-subscriptions.v1.yaml (HC-204).

A device registers, lists, and removes its UnifiedPush subscriptions. The body has the
W3C PushSubscription JSON shape (endpoint, keys.p256dh, keys.auth). The endpoint is a
capability URL, so answers give only its host. Callers are not authenticated (demo
depth): who may register a device for a recipient is OPEN.
"""

import base64
import binascii
import re
from typing import Annotated, Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from adapters.inbound.http.problems import problem_response
from application.push import (
    ListPushSubscriptions,
    PushEndpointNotAllowed,
    RegisterPushSubscription,
    UnregisterPushSubscription,
)
from domain.push import PushSubscription
from domain.validation import DomainValidationError

_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
INVALID = "https://hackcure.org/errors/invalid-push-subscription"


class KeysBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p256dh: Annotated[str, Field(min_length=1, max_length=200)]
    auth: Annotated[str, Field(min_length=1, max_length=100)]


class SubscriptionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint: Annotated[str, Field(min_length=1, max_length=2048)]
    keys: KeysBody


def _b64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _wire(subscription: PushSubscription) -> dict:
    return {
        "subscription_id": subscription.subscription_id,
        "recipient_ref": subscription.recipient_ref,
        "channel": "push",
        "endpoint_host": subscription.endpoint_host,
        "registered_at": subscription.registered_at.isoformat(),
    }


def _invalid(detail: str) -> Any:
    return problem_response(
        status=400,
        title="Invalid Push Subscription",
        detail=detail,
        type_uri=INVALID,
    )


def create_push_subscriptions_router(
    register: RegisterPushSubscription,
    unregister: UnregisterPushSubscription,
    list_subscriptions: ListPushSubscriptions,
) -> APIRouter:
    router = APIRouter(prefix="/v1/recipients/{recipient_ref}/push-subscriptions")

    @router.post("", status_code=201)
    async def register_push_subscription(recipient_ref: str, request: Request) -> Any:
        if not _REF.fullmatch(recipient_ref):
            return _invalid("recipient_ref must be an opaque reference.")
        try:
            body = SubscriptionBody.model_validate_json(await request.body())
            p256dh, auth = _b64url(body.keys.p256dh), _b64url(body.keys.auth)
        except ValidationError as error:
            fields = sorted(
                {".".join(map(str, e["loc"])) or "body" for e in error.errors()}
            )
            return _invalid("Invalid or missing fields: " + ", ".join(fields))
        except (binascii.Error, ValueError):
            return _invalid("keys must be base64url-encoded.")
        try:
            subscription = register.execute(recipient_ref, body.endpoint, p256dh, auth)
        except PushEndpointNotAllowed as error:
            return problem_response(
                status=400,
                title="Push Server Not Allowed",
                detail=str(error),
                type_uri="https://hackcure.org/errors/push-endpoint-not-allowed",
            )
        except DomainValidationError as error:
            return _invalid(str(error))
        return _wire(subscription)

    @router.get("")
    def list_push_subscriptions(recipient_ref: str) -> Any:
        if not _REF.fullmatch(recipient_ref):
            return _invalid("recipient_ref must be an opaque reference.")
        subscriptions = list_subscriptions.execute(recipient_ref)
        return {
            "recipient_ref": recipient_ref,
            "count": len(subscriptions),
            "subscriptions": [_wire(s) for s in subscriptions],
        }

    @router.delete("/{subscription_id}", response_model=None)
    def remove_push_subscription(recipient_ref: str, subscription_id: str) -> Any:
        if not unregister.execute(recipient_ref, subscription_id):
            return problem_response(
                status=404,
                title="Push Subscription Not Found",
                detail=f"No push subscription {subscription_id!r} for this recipient.",
                type_uri="https://hackcure.org/errors/push-subscription-not-found",
            )
        return Response(status_code=204)

    return router
