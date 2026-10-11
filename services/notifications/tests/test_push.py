"""Mobile push (HC-204): encryption, subscriptions, delivery, gateway, and HTTP.

Push servers are replaced by httpx MockTransport and gateway doubles: test doubles only.
The live delivery through ntfy is documented in the README.
"""

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from adapters.inbound.http.push_subscriptions import create_push_subscriptions_router
from adapters.outbound.in_memory_push_subscriptions import (
    InMemoryPushSubscriptionStore,
)
from adapters.outbound.unifiedpush_gateway import UnifiedPushGateway
from adapters.outbound.webpush_encryption import encrypt
from application.push import (
    ListPushSubscriptions,
    PushDeliveryProvider,
    PushEndpointNotAllowed,
    PushOutcome,
    PushResult,
    RegisterPushSubscription,
    UnregisterPushSubscription,
)
from domain.models import (
    AlertMetadata,
    Channel,
    DeliveryStatus,
    NotificationCategory,
    NotificationPayload,
    Priority,
    RecipientRole,
)
from domain.push import PushSubscription, push_message
from domain.validation import DomainValidationError
from tests.webpush_receiver import Receiver

NOW = datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc)
ENDPOINT = "https://ntfy.sh/upAbCdEfGhIjKlMnOpQrStUv?up=1"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def subscription_for(recipient="pat-a", receiver=None, endpoint=ENDPOINT, sid="psub-1"):
    receiver = receiver or Receiver()
    return PushSubscription(
        sid, recipient, endpoint, receiver.p256dh, receiver.auth, NOW
    )


def payload(category=NotificationCategory.ALERT, priority=Priority.HIGH):
    return NotificationPayload(
        notification_id="notif-1",
        recipient_ref="pat-a",
        recipient_role=RecipientRole.PATIENT,
        category=category,
        priority=priority,
        title="HbA1c au-dessus de la plage de référence",
        body="HbA1c 8,9 % (référence 4,0-6,0 %).",
        channels=[Channel.PUSH],
        alert_metadata=AlertMetadata(),
    )


class AcceptingGateway:
    def __init__(self, outcomes=None):
        self.sent = []
        self.outcomes = list(outcomes or [])

    def send(self, subscription, message, urgency):
        self.sent.append((subscription.subscription_id, message, urgency))
        outcome = self.outcomes.pop(0) if self.outcomes else PushOutcome.ACCEPTED
        return PushResult(outcome)


# --- RFC 8291 encryption -------------------------------------------------------------


def test_encryption_reproduces_the_rfc_8291_test_vector():
    """RFC 8291, Appendix A: same keys and salt, byte-identical message."""
    sender = ec.derive_private_key(
        int.from_bytes(unb64("yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"), "big"),
        ec.SECP256R1(),
    )
    body = encrypt(
        b"When I grow up, I want to be a watermelon",
        unb64(
            "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZ"
            "GH6SRpkNtoIAiw4"
        ),
        unb64("BTBZMqHH6r4Tts7J_aSIgg"),
        sender_key=sender,
        salt=unb64("DGv6ra1nlYgDCS1FRnbzlw"),
    )

    assert b64(body) == (
        "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3"
        "vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuw"
        "XPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN"
    )


def test_a_device_decrypts_what_it_is_sent_and_nobody_else_can():
    device, other = Receiver(), Receiver()
    body = encrypt(b"bonjour", device.p256dh, device.auth)

    assert device.decrypt(body) == b"bonjour"
    with pytest.raises(Exception):
        other.decrypt(body)


# --- Domain ---------------------------------------------------------------------------


def test_the_push_message_carries_no_clinical_text():
    message = json.loads(push_message(payload()))

    assert message == {
        "v": 1,
        "notification_id": "notif-1",
        "category": "alert",
        "priority": "high",
        "title": "Nouvelle alerte à consulter",
        "fictional": True,
    }
    raw = push_message(payload()).decode()
    assert "HbA1c" not in raw and "8,9" not in raw


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"endpoint": "http://ntfy.sh/up1"}, "https"),
        ({"endpoint": "https://user:pw@ntfy.sh/up1"}, "credentials"),
        ({"p256dh": b"\x04" + b"0" * 10}, "p256dh"),
        ({"auth": b"short"}, "auth"),
    ],
)
def test_an_invalid_subscription_is_refused(changes, message):
    fields = {
        "subscription_id": "s",
        "recipient_ref": "pat-a",
        "endpoint": ENDPOINT,
        "p256dh": Receiver().p256dh,
        "auth": b"0" * 16,
        "registered_at": NOW,
        **changes,
    }
    with pytest.raises(DomainValidationError, match=message):
        PushSubscription(**fields)


# --- Registration and delivery ----------------------------------------------------


def register(store, endpoint=ENDPOINT, receiver=None):
    receiver = receiver or Receiver()
    use_case = RegisterPushSubscription(
        store, frozenset({"ntfy.sh"}), clock=lambda: NOW
    )
    return use_case.execute("pat-a", endpoint, receiver.p256dh, receiver.auth)


def test_only_allowed_push_servers_can_be_registered():
    with pytest.raises(PushEndpointNotAllowed):
        register(InMemoryPushSubscriptionStore(), "https://169.254.169.254/latest")


def test_registering_the_same_endpoint_again_replaces_its_keys():
    store = InMemoryPushSubscriptionStore()
    first = register(store)
    second = register(store)

    assert first.subscription_id == second.subscription_id
    assert store.list_for_recipient("pat-a") == [second]


def test_without_a_registered_device_push_fails_explicitly():
    record = PushDeliveryProvider(
        InMemoryPushSubscriptionStore(), AcceptingGateway()
    ).deliver("pat-a", payload())

    assert (record.status, record.failure_reason) == (
        DeliveryStatus.FAILED,
        "push_subscription_not_registered",
    )


def test_an_accepted_push_is_sent_not_delivered_with_the_priority_as_urgency():
    store, gateway = InMemoryPushSubscriptionStore(), AcceptingGateway()
    store.save(subscription_for())

    record = PushDeliveryProvider(store, gateway).deliver("pat-a", payload())

    assert record.status is DeliveryStatus.SENT
    [(sid, message, urgency)] = gateway.sent
    assert (sid, urgency) == ("psub-1", "high")
    assert json.loads(message)["notification_id"] == "notif-1"


def test_a_gone_endpoint_is_removed_and_the_push_fails():
    store = InMemoryPushSubscriptionStore()
    store.save(subscription_for())

    record = PushDeliveryProvider(store, AcceptingGateway([PushOutcome.GONE])).deliver(
        "pat-a", payload()
    )

    assert (record.status, record.failure_reason) == (
        DeliveryStatus.FAILED,
        "push_endpoint_gone",
    )
    assert store.list_for_recipient("pat-a") == []


def test_one_accepting_device_is_enough_and_failures_are_named():
    store = InMemoryPushSubscriptionStore()
    store.save(subscription_for(sid="psub-1"))
    store.save(subscription_for(sid="psub-2", endpoint=ENDPOINT + "2"))

    sent = PushDeliveryProvider(
        store, AcceptingGateway([PushOutcome.RATE_LIMITED, PushOutcome.ACCEPTED])
    ).deliver("pat-a", payload())
    failed = PushDeliveryProvider(
        store, AcceptingGateway([PushOutcome.RATE_LIMITED, PushOutcome.REJECTED])
    ).deliver("pat-a", payload())

    assert sent.status is DeliveryStatus.SENT
    assert failed.failure_reason == "push_rate_limited+push_server_rejected"


# --- Gateway over HTTP ------------------------------------------------------------


def test_the_gateway_posts_an_encrypted_web_push_the_device_can_read():
    device = Receiver()
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(201)

    result = UnifiedPushGateway(transport=httpx.MockTransport(handler)).send(
        subscription_for(receiver=device), b'{"v":1}', "high"
    )

    [request] = seen
    assert result.outcome is PushOutcome.ACCEPTED
    assert str(request.url) == ENDPOINT
    assert request.headers["content-encoding"] == "aes128gcm"
    assert request.headers["urgency"] == "high"
    assert int(request.headers["ttl"]) > 0
    assert device.decrypt(request.content) == b'{"v":1}'


@pytest.mark.parametrize(
    "response, outcome",
    [
        (httpx.Response(200), PushOutcome.ACCEPTED),
        (httpx.Response(404), PushOutcome.GONE),
        (httpx.Response(429), PushOutcome.RATE_LIMITED),
        (httpx.Response(413), PushOutcome.REJECTED),
        (httpx.Response(500), PushOutcome.REJECTED),
        # A redirect is never followed: the push server does not get to choose a target.
        (
            httpx.Response(307, headers={"location": "https://x.test"}),
            PushOutcome.REJECTED,
        ),
    ],
)
def test_the_gateway_maps_push_server_answers(response, outcome):
    gateway = UnifiedPushGateway(transport=httpx.MockTransport(lambda r: response))

    assert gateway.send(subscription_for(), b"x", "normal").outcome is outcome


def test_an_unreachable_push_server_is_a_rejection():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    result = UnifiedPushGateway(transport=httpx.MockTransport(handler)).send(
        subscription_for(), b"x", "normal"
    )

    assert result.outcome is PushOutcome.REJECTED


# --- HTTP API ---------------------------------------------------------------------


def client(store=None):
    store = store or InMemoryPushSubscriptionStore()
    app = FastAPI()
    app.include_router(
        create_push_subscriptions_router(
            RegisterPushSubscription(store, frozenset({"ntfy.sh"})),
            UnregisterPushSubscription(store),
            ListPushSubscriptions(store),
        )
    )
    return TestClient(app)


def body(receiver=None, endpoint=ENDPOINT):
    receiver = receiver or Receiver()
    return {
        "endpoint": endpoint,
        "keys": {"p256dh": b64(receiver.p256dh), "auth": b64(receiver.auth)},
    }


PATH = "/v1/recipients/pat-a/push-subscriptions"


def test_register_list_and_remove_a_device_without_exposing_its_endpoint():
    api = client()

    created = api.post(PATH, json=body())
    listed = api.get(PATH).json()

    assert created.status_code == 201
    assert created.json()["endpoint_host"] == "ntfy.sh"
    assert "endpoint" not in created.json()
    assert ENDPOINT not in json.dumps(listed)
    assert listed["count"] == 1
    sid = created.json()["subscription_id"]
    assert api.delete(f"{PATH}/{sid}").status_code == 204
    assert api.delete(f"{PATH}/{sid}").status_code == 404
    assert api.get(PATH).json()["count"] == 0


@pytest.mark.parametrize(
    "request_body, title",
    [
        (body(endpoint="https://evil.test/up"), "Push Server Not Allowed"),
        # An allowed host, but not https: refused by the domain.
        (body(endpoint="http://ntfy.sh/up"), "Invalid Push Subscription"),
        (
            {**body(), "keys": {"p256dh": "!!", "auth": "x"}},
            "Invalid Push Subscription",
        ),
        (
            {**body(), "keys": {"p256dh": b64(b"\x04" * 10), "auth": b64(b"0" * 16)}},
            "Invalid Push Subscription",
        ),
        ({"endpoint": ENDPOINT}, "Invalid Push Subscription"),
        ({**body(), "extra": 1}, "Invalid Push Subscription"),
    ],
)
def test_an_invalid_registration_is_a_400(request_body, title):
    response = client().post(PATH, json=request_body)

    assert response.status_code == 400
    assert response.json()["title"] == title


def test_a_recipient_reference_must_be_opaque():
    assert (
        client()
        .post("/v1/recipients/Le%C3%AFla Mansouri/push-subscriptions", json=body())
        .status_code
        == 400
    )


# --- Contract conformance -------------------------------------------------------------

CONTRACT = yaml.safe_load(
    (
        Path(__file__).resolve().parents[3]
        / "contracts/api/notifications/push-subscriptions.v1.yaml"
    ).read_text(encoding="utf-8")
)


def conforms(instance, schema):
    validator = Draft202012Validator(
        {**schema, "components": CONTRACT["components"]}, format_checker=FormatChecker()
    )
    errors = [e.message for e in validator.iter_errors(instance)]
    assert not errors, errors


def test_requests_and_answers_follow_the_contract():
    operation = CONTRACT["paths"]["/v1/recipients/{recipient_ref}/push-subscriptions"]
    api = client()
    request_body = body()
    conforms(request_body, {"$ref": "#/components/schemas/PushSubscriptionRequest"})

    created = api.post(PATH, json=request_body)
    conforms(created.json(), {"$ref": "#/components/schemas/PushSubscription"})
    listed = api.get(PATH).json()
    conforms(
        listed,
        operation["get"]["responses"]["200"]["content"]["application/json"]["schema"],
    )
    refused = api.post(PATH, json=body(endpoint="https://evil.test/up"))
    conforms(refused.json(), {"$ref": "#/components/schemas/Problem"})


def test_the_contract_example_registers():
    operation = CONTRACT["paths"]["/v1/recipients/{recipient_ref}/push-subscriptions"]
    example = operation["post"]["requestBody"]["content"]["application/json"][
        "examples"
    ]["patientPhone"]["value"]

    assert client().post(PATH, json=example).status_code == 201
