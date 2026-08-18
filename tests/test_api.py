from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.exceptions import IdempotencyConflictError


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_payment_requires_api_key(client: TestClient) -> None:
    response = client.post(
        "/api/v1/payments",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "amount": "10.00",
            "currency": "RUB",
            "description": "test",
            "webhook_url": "https://example.com/hook",
        },
    )
    assert response.status_code == 401


def test_create_payment_requires_idempotency_key(client: TestClient, api_headers: dict[str, str]) -> None:
    headers = dict(api_headers)
    headers.pop("Idempotency-Key")
    response = client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "amount": "10.00",
            "currency": "RUB",
            "description": "test",
            "webhook_url": "https://example.com/hook",
        },
    )
    assert response.status_code == 422


def test_create_payment_rejects_non_positive_amount(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/payments",
        headers=api_headers,
        json={
            "amount": "0",
            "currency": "RUB",
            "description": "test",
            "webhook_url": "https://example.com/hook",
        },
    )
    assert response.status_code == 422


def test_create_payment_accepted(client: TestClient, api_headers: dict[str, str], sample_payment) -> None:
    response = client.post(
        "/api/v1/payments",
        headers=api_headers,
        json={
            "amount": "150.50",
            "currency": "RUB",
            "description": "Test payment",
            "metadata": {"order_id": "42"},
            "webhook_url": "https://example.com/webhook",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["payment_id"] == str(sample_payment.id)
    assert body["status"] == "pending"
    assert "created_at" in body


def test_get_payment(client: TestClient, sample_payment) -> None:
    response = client.get(
        f"/api/v1/payments/{sample_payment.id}",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(sample_payment.id)
    assert body["metadata"] == {"order_id": "42"}
    assert body["amount"] == "150.50"
    assert body["status"] == "pending"
    assert body["idempotency_key"] == "key-1"


def test_get_payment_requires_api_key(client: TestClient, sample_payment) -> None:
    response = client.get(f"/api/v1/payments/{sample_payment.id}")
    assert response.status_code == 401


def test_get_payment_not_found(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/payments/{uuid4()}",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404


def test_create_payment_conflict(client: TestClient, api_headers: dict[str, str], monkeypatch) -> None:
    async def conflict(*args, **kwargs):  # noqa: ANN002, ANN003
        raise IdempotencyConflictError

    monkeypatch.setattr("app.api.v1.payments.payment_service.create_payment", conflict)
    response = client.post(
        "/api/v1/payments",
        headers=api_headers,
        json={
            "amount": "10.00",
            "currency": "USD",
            "description": "test",
            "webhook_url": "https://example.com/hook",
        },
    )
    assert response.status_code == 409
