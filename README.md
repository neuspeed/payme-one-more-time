# Асинхронный сервис процессинга платежей

Микросервис для асинхронной обработки платежей: принимает запросы на оплату,
публикует события через Outbox pattern в RabbitMQ, обрабатывает их в consumer’е
с эмуляцией платёжного шлюза и уведомляет клиента через webhook.

## Стек

- Python 3.12, FastAPI, Pydantic v2
- SQLAlchemy 2.0 (async) + PostgreSQL 16
- RabbitMQ 3.13 + FastStream
- Alembic (async-миграции)
- Docker + docker-compose

## Архитектура

    ┌────────┐   POST /payments    ┌──────────────┐
    │ Client │ ──────────────────► │  FastAPI API │
    └────────┘                     └──────┬───────┘
                                          │ 1 транзакция
                                          ▼
                                   ┌──────────────┐
                                   │  PostgreSQL  │
                                   │ payments +   │
                                   │   outbox     │
                                   └──────┬───────┘
                                          │ poll
                                          ▼
                                   ┌──────────────┐
                                   │   Outbox     │
                                   │  publisher   │
                                   └──────┬───────┘
                                          │ publish
                                          ▼
                                   ┌──────────────┐
                                   │   RabbitMQ   │
                                   │ payments.new │
                                   │  + retry/DLQ │
                                   └──────┬───────┘
                                          │ consume
                                          ▼
                                   ┌──────────────┐
                                   │   Consumer   │
                                   │  + webhook   │
                                   └──────────────┘

API не публикует в RabbitMQ напрямую: запись платежа и событие в `outbox`
происходят в одной транзакции. Отдельный процесс читает `outbox` и публикует
события в брокер — это даёт гарантию доставки at-least-once даже при падении
RabbitMQ или API.

## Структура

    app/
      api/            # HTTP-эндпоинты FastAPI
      broker/         # RabbitMQ: broker, exchange, очереди, retry, DLQ
      consumer/       # обработчик payments.new, эмуляция шлюза, webhook
      core/           # Base, async engine, session
      models/         # SQLAlchemy-модели: Payment, Outbox
      outbox/         # publisher из outbox в RabbitMQ
      schemas/        # Pydantic-схемы
    alembic/          # миграции
    docker-compose.yml
    Dockerfile
    .env.example

## Запуск

1. Скопировать пример конфига:

       cp .env.example .env

2. Поднять окружение:

       docker compose up --build

3. Дождаться, пока все сервисы станут healthy. API будет доступен на
   http://localhost:8000, RabbitMQ management — на http://localhost:15672.

Swagger: http://localhost:8000/docs

По умолчанию `API_KEY=super-secret-key`. Можно поменять в `.env`.

## Примеры

### Создать платёж

    curl -X POST http://localhost:8000/api/v1/payments \
      -H "X-API-Key: super-secret-key" \
      -H "Idempotency-Key: 11111111-1111-1111-1111-111111111111" \
      -H "Content-Type: application/json" \
      -d '{
        "amount": "100.50",
        "currency": "rub",
        "description": "Оплата заказа #42",
        "meta": {"order_id": 42},
        "webhook_url": "https://webhook.site/your-uuid"
      }'

Ответ 202:

    {
      "payment_id": "uuid",
      "status": "pending",
      "created_at": "2026-01-01T12:00:00Z"
    }

### Получить платёж

    curl http://localhost:8000/api/v1/payments/<payment_id> \
      -H "X-API-Key: super-secret-key"