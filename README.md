# FastAPI + Kafka + Postgres + Socket.IO (Docker Compose Demo)

A small, **portfolio-ready** reference project that demonstrates:

- **FastAPI** REST API
- **Kafka** event publishing + consuming
- **PostgreSQL** persistence via async **SQLAlchemy 2.x**
- **Socket.IO** real-time broadcast to connected clients
- Local orchestration via **Docker Compose**
- **Pytest** integration test (optional toggle)
- **Postman** collection + environment file

This is intentionally simple, but **production-minded** (typed, async, readable, easy to extend).

---

## Architecture

1. Client calls `POST /events` with an `event_type` + JSON payload.
2. API publishes the event to Kafka topic `demo.events.incoming`.
3. Background consumer reads from Kafka, persists the event to Postgres, and emits `new_event` to all Socket.IO clients.
4. Client can query persisted events via `GET /events`.

```
┌─────────────┐   POST /events     ┌──────────────┐    Kafka topic     ┌──────────────┐
│   Client    │ ───────────────▶   │   FastAPI    │ ───────────────▶   │    Kafka     │
│ (Postman,   │                    │  API+SIO     │                    │   Broker     │
│  browser)   │ ◀──── Socket.IO ───│ (consumer)   │◀────── consumer ───│              │
└─────────────┘    new_event       └──────────────┘                    └──────────────┘
                                   │
                                   │ SQLAlchemy
                                   ▼
                              ┌──────────────┐
                              │  PostgreSQL   │
                              └──────────────┘
```

---

## Quick start

### 1) Run everything (Docker)

```bash
docker compose up --build
```
#### Or with makefile
```bash
make up
make down
make test
```

API will be available at:
- REST: `http://localhost:8000`
- Docs (Swagger): `http://localhost:8000/docs`
- Socket.IO path: `http://localhost:8000/socket.io/`

### 2) Queue an event

```bash
curl -X POST http://localhost:8000/events \
  -H 'Content-Type: application/json' \
  -d '{"event_type": "demo.cli", "payload": {"hello": "world"}}'
```

### 3) List persisted events

```bash
curl http://localhost:8000/events
```

---

## Socket.IO client example

### Browser (CDN)

```html
<script src="https://cdn.jsdelivr.net/npm/socket.io-client@4/dist/socket.io.min.js"></script>
<script>
  const socket = io("http://localhost:8000");

  socket.on("connect", () => console.log("connected", socket.id));
  socket.on("server_hello", (msg) => console.log("server_hello", msg));
  socket.on("new_event", (e) => console.log("new_event", e));
</script>
```

---

## Pytest integration test

The repo includes an end-to-end test that:
- posts an event
- polls `/events` until the record is persisted

Run it like this:

```bash
# Start services
docker compose up --build -d

# Run integration tests (opt-in)
RUN_INTEGRATION_TESTS=1 pytest -q
```

You can override the API base URL:

```bash
API_BASE_URL=http://localhost:8000 RUN_INTEGRATION_TESTS=1 pytest -q
```

---

## Postman tests

Import these files into Postman:
- `postman/collection.json`
- `postman/environment.json`

Then run the collection using the **Local Demo** environment.

---

## Project layout

```
.
├── app/
│   ├── main.py              # FastAPI app + background Kafka consumer + Socket.IO wrapper
│   ├── kafka_client.py      # Producer/consumer wrapper + topic bootstrap
│   ├── db.py                # Async SQLAlchemy session + engine
│   ├── models.py            # Event model
│   ├── sockets.py           # Socket.IO server events
│   └── config.py            # Env-driven settings
├── tests/
│   └── test_end_to_end.py   # Optional end-to-end test
├── postman/
│   ├── collection.json
│   └── environment.json
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Notes / next extensions (optional)

If you want to extend this demo into a bigger portfolio piece:

- Add a separate `worker` service container to isolate the Kafka consumer
- Add Alembic migrations (instead of `create_all`)
- Add structured logging + OpenTelemetry exports
- Add a simple UI client (React/Vue) that connects to Socket.IO and renders live events

---

## License

MIT
