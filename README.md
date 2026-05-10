# GridSense

GridSense is a prototype smart power grid analytics platform for the **Advanced Data Management** project.

From an engineering point of view, the goal is to design and build a small but realistic distributed data system that shows why different storage technologies are useful for different workloads.

The project models a regional power grid where engineers need to ingest sensor readings, analyze fault propagation, store equipment metadata, manage billing records, and serve fast dashboard views.

## API package structure

The runnable FastAPI app now uses the Part B handout layout directly under `api/`. The API container starts `uvicorn main:app`.

```text
api/
  main.py
  routers/
    sensors.py
    grid.py
    equipment.py
    billing.py
    alerts.py
  models/
    cassandra.py
    graph.py
    mongo.py
    postgres.py
  db/
    cassandra.py
    neo4j.py
    mongo.py
    postgres.py
    redis.py
```

The FastAPI gateway exposes the required Cassandra, Neo4j, MongoDB, PostgreSQL, and Redis endpoints. The route handlers are async: Neo4j uses `AsyncGraphDatabase`, MongoDB uses Motor, PostgreSQL uses an `asyncpg` pool, Redis uses `redis.asyncio`, and Cassandra uses async futures from `cassandra-driver`. PostgreSQL billing uses JSONB tariff rules for invoice calculation, Cassandra stores readings in both sensor-oriented and dashboard-oriented tables, Redis caches sensor summaries and active alerts, MongoDB keeps heterogeneous equipment documents, and Neo4j handles topology traversal.

## Local verification

Start the stack:

```bash
docker compose up --build
```

With Podman Compose, use:

```bash
podman compose up --build
```

If you are using Fedora/Podman and the API container remains in `Created` after the databases are healthy, start it manually:

```bash
podman start gridsense_api
```

Check the API health endpoint:

```bash
curl http://localhost:8000/health
```

Check billing customers:

```bash
curl http://localhost:8000/billing/customers
```

Check active tariffs:

```bash
curl http://localhost:8000/billing/tariffs
```

Check recent bills:

```bash
curl http://localhost:8000/billing/bills
```

Populate the larger assessment data set after the services are healthy:

```bash
python scripts/seed.py
```

The script is idempotent and creates 10 substations, 40 transformers, 200 smart meters, 50,000 sensor readings across 20 sensors, 30 equipment records, and 100 billing accounts with invoices.

Check PostgreSQL seed counts:

```bash
docker compose exec -T billing-db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT count(*) AS customers FROM customers;" \
  -c "SELECT count(*) AS premises FROM premises;" \
  -c "SELECT count(*) AS tariffs FROM tariffs;" \
  -c "SELECT count(*) AS bills FROM bills;"'
```

Create a bill using a real premise ID:

```bash
PREMISE_ID=$(docker compose exec -T billing-db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT premise_id FROM premises ORDER BY created_at LIMIT 1"')

curl -X POST http://localhost:8000/billing/bills \
  -H 'Content-Type: application/json' \
  -d "{
    \"premise_id\": \"${PREMISE_ID}\",
    \"billing_month\": \"2026-05-01\",
    \"total_kwh\": \"240.500\",
    \"total_amount\": \"48.25\",
    \"status\": \"ISSUED\"
  }"
```

Generate an invoice using tariff JSONB rules:

```bash
PREMISE_ID=$(docker compose exec -T billing-db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT premise_id FROM premises ORDER BY created_at LIMIT 1"')

curl -X POST http://localhost:8000/billing/invoice \
  -H 'Content-Type: application/json' \
  -d "{
    \"premise_id\": \"${PREMISE_ID}\",
    \"billing_month\": \"2026-05-01\",
    \"total_kwh\": \"315.250\"
  }"
```

Fetch account balance and bill history:

```bash
curl "http://localhost:8000/billing/account/${PREMISE_ID}"
```

## Sensor API examples

Ingest one reading:

```bash
curl -X POST http://localhost:8000/sensors/readings \
  -H 'Content-Type: application/json' \
  -d '{
    "sensor_id": "SENSOR_DEMO",
    "reading_time": "2026-05-10T12:00:00Z",
    "metric_type": "voltage",
    "value": 229.4,
    "unit": "V",
    "quality_flag": 0,
    "district_id": "DISTRICT_01"
  }'
```

Read latest values and cached summary:

```bash
curl "http://localhost:8000/sensors/SENSOR_DEMO/readings?limit=10"
curl http://localhost:8000/sensors/SENSOR_DEMO/summary
```

## Grid and alert examples

Fault impact traversal:

```bash
curl "http://localhost:8000/grid/fault-impact/SS_001?max_depth=4"
```

Publish and read active alerts:

```bash
curl -X POST http://localhost:8000/alerts/publish \
  -H 'Content-Type: application/json' \
  -d '{"node_id": "TX_001_A", "severity": "critical", "message": "Transformer overload"}'

curl http://localhost:8000/alerts/active
```

## Equipment API examples

List equipment metadata:

```bash
curl http://localhost:8000/equipment
```

List transformers:

```bash
curl "http://localhost:8000/equipment?type=transformer"
```

Get one equipment document:

```bash
curl http://localhost:8000/equipment/TX_001_A
```

Get a transformer and linked equipment:

```bash
curl http://localhost:8000/equipment/transformer/TX_001_A
```

Register flexible equipment metadata:

```bash
DEMO_EQUIPMENT_ID="SM_DEMO_$(date +%s)"

curl -X POST http://localhost:8000/equipment \
  -H 'Content-Type: application/json' \
  -d "{
    \"equipment_id\": \"${DEMO_EQUIPMENT_ID}\",
    \"type\": \"smart_meter\",
    \"manufacturer\": \"DemoGrid\",
    \"transformer_id\": \"TX_001_A\",
    \"telemetry_fields\": [\"voltage\", \"current\", \"energy_kwh\"]
  }"
```

Patch equipment metadata:

```bash
curl -X PATCH "http://localhost:8000/equipment/${DEMO_EQUIPMENT_ID}" \
  -H 'Content-Type: application/json' \
  -d '{"firmware": "1.0.1", "commissioning_status": "verified"}'
```

Check MongoDB equipment seed data:

```bash
docker compose exec -T catalog-db mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin gridsense_catalog --eval "db.equipment.countDocuments(); db.equipment.find().limit(3).pretty();"
```
