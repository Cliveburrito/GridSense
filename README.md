# GridSense

GridSense is a prototype smart power grid analytics platform for the **Advanced Data Management** project.

From an engineering point of view, the goal is to design and build a small but realistic distributed data system that shows why different storage technologies are useful for different workloads.

The project models a regional power grid where engineers need to ingest sensor readings, analyze fault propagation, store equipment metadata, manage billing records, and serve fast dashboard views.

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
