# Payment Processing Service

Асинхронный сервис обработки платежей. Принимает запрос на оплату, обрабатывает его через эмуляцию платёжного шлюза и отправляет результат на webhook.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Миграции запускаются при старте контейнеров (`alembic upgrade head`).

## API

Оба эндпоинта требуют заголовок `X-API-Key`.

### Создать платёж

`POST /api/v1/payments`

Обязательный заголовок `Idempotency-Key`. Повтор с тем же ключом и тем же телом возвращает исходный платёж. Тот же ключ с другим телом — `409`.

### Получить платёж

`GET /api/v1/payments/{payment_id}`

Статусы: `pending`, `succeeded`, `failed`.

## Как устроено

1. Создание платежа и запись в `outbox` идут в одной транзакции.
2. Фоновый цикл в API публикует неопубликованные события в очередь `payments.new`.
3. Consumer эмулирует шлюз (2–5 секунд, 90% `succeeded` / 10% `failed`), обновляет статус и шлёт webhook.
4. Ошибка обработки или webhook: 3 попытки с задержками 2s, 4s, 8s. После третьей — `payments.new.dlq`.

## Тесты

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```
