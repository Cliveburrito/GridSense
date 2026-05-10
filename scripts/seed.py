from __future__ import annotations

import asyncio
import os
import random
import socket
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import NAMESPACE_DNS, uuid5

import asyncpg
from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args
from neo4j import GraphDatabase
from pymongo import MongoClient


ROOT = Path(__file__).resolve().parents[1]


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    return {**values, **os.environ}


def reachable_host(host: str) -> str:
    try:
        socket.gethostbyname(host)
        return host
    except socket.gaierror:
        return "localhost"


def reachable_neo4j_uri(uri: str) -> str:
    parsed = urlparse(uri)
    host = parsed.hostname
    if host is None:
        return uri
    try:
        socket.gethostbyname(host)
        return uri
    except socket.gaierror:
        if host == "graph-db":
            netloc = parsed.netloc.replace("graph-db", "localhost", 1)
            return urlunparse(parsed._replace(netloc=netloc))
        return uri


def bucket_minute(reading_time: datetime) -> str:
    return reading_time.astimezone(timezone.utc).strftime("%Y%m%d%H%M")


def seed_cassandra(env: dict[str, str]) -> None:
    host = reachable_host(env.get("CASSANDRA_HOST", "timeseries-db"))
    port = int(env.get("CASSANDRA_PORT", "9042"))
    keyspace = env.get("CASSANDRA_KEYSPACE", "gridsense")
    cluster = Cluster([host], port=port)
    session = cluster.connect(keyspace)

    insert_by_sensor = session.prepare(
        """
        INSERT INTO sensor_readings (
            sensor_id, reading_time, metric_type, value, unit, quality_flag
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """
    )
    insert_by_bucket = session.prepare(
        """
        INSERT INTO sensor_readings_by_bucket (
            bucket_minute, district_id, metric_type, reading_time,
            sensor_id, value, unit, quality_flag
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    )

    start = datetime(2026, 5, 10, 0, 0, 0, tzinfo=timezone.utc)
    sensor_params = []
    bucket_params = []
    metrics = [
        ("voltage", "V", 228.0, 8.0),
        ("current", "A", 42.0, 12.0),
        ("power_factor", "ratio", 0.94, 0.04),
        ("temp", "C", 54.0, 7.0),
    ]

    for sensor_index in range(20):
        sensor_id = f"SENSOR_{sensor_index + 1:03d}"
        district_id = f"DISTRICT_{(sensor_index % 5) + 1:02d}"
        for offset in range(2500):
            metric_type, unit, base, spread = metrics[offset % len(metrics)]
            reading_time = start + timedelta(seconds=offset * 2 + sensor_index)
            value = round(base + random.uniform(-spread, spread), 3)
            quality_flag = 0 if random.random() > 0.02 else 1
            sensor_params.append(
                (sensor_id, reading_time, metric_type, value, unit, quality_flag)
            )
            bucket_params.append(
                (
                    bucket_minute(reading_time),
                    district_id,
                    metric_type,
                    reading_time,
                    sensor_id,
                    value,
                    unit,
                    quality_flag,
                )
            )

    execute_concurrent_with_args(
        session,
        insert_by_sensor,
        sensor_params,
        concurrency=100,
        raise_on_first_error=True,
    )
    execute_concurrent_with_args(
        session,
        insert_by_bucket,
        bucket_params,
        concurrency=100,
        raise_on_first_error=True,
    )
    cluster.shutdown()
    print("Seeded Cassandra: 50,000 readings across 20 sensors.")


def seed_neo4j(env: dict[str, str]) -> None:
    password = env["NEO4J_PASSWORD"]
    uri = reachable_neo4j_uri(env.get("NEO4J_URI", "bolt://graph-db:7687"))
    driver = GraphDatabase.driver(uri, auth=(env.get("NEO4J_USER", "neo4j"), password))

    cypher = """
    CREATE CONSTRAINT gsp_id IF NOT EXISTS
    FOR (g:GridSupplyPoint) REQUIRE g.gsp_id IS UNIQUE;
    CREATE CONSTRAINT substation_id IF NOT EXISTS
    FOR (s:Substation) REQUIRE s.substation_id IS UNIQUE;
    CREATE CONSTRAINT transformer_id IF NOT EXISTS
    FOR (t:Transformer) REQUIRE t.asset_id IS UNIQUE;
    CREATE CONSTRAINT meter_id IF NOT EXISTS
    FOR (m:SmartMeter) REQUIRE m.meter_id IS UNIQUE;
    MERGE (g:GridSupplyPoint {gsp_id: 'GSP_NORTH'})
    SET g.name = 'Northern Grid Supply Point', g.voltage_kV = 132, g.region = 'North Metro';
    """
    with driver.session(database="neo4j") as session:
        for statement in [part.strip() for part in cypher.split(";") if part.strip()]:
            session.run(statement)

        for s in range(1, 11):
            substation_id = f"SS_{s:03d}"
            session.run(
                """
                MATCH (g:GridSupplyPoint {gsp_id: 'GSP_NORTH'})
                MERGE (s:Substation {substation_id: $substation_id})
                SET s.node_id = $substation_id,
                    s.name = $name,
                    s.voltage_kV = 11,
                    s.lat = 39.30 + ($idx * 0.01),
                    s.lon = 22.90 + ($idx * 0.01),
                    s.commissioned_year = 1995 + $idx
                MERGE (g)-[:FEEDS {feeder_id: $feeder_id}]->(s)
                """,
                substation_id=substation_id,
                name=f"Metro Substation {s:03d}",
                idx=s,
                feeder_id=f"F_{s:03d}",
            )

            for t in range(1, 5):
                transformer_number = ((s - 1) * 4) + t
                asset_id = f"TX_{transformer_number:03d}"
                session.run(
                    """
                    MATCH (s:Substation {substation_id: $substation_id})
                    MERGE (t:Transformer {asset_id: $asset_id})
                    SET t.node_id = $asset_id,
                        t.rating_kVA = $rating,
                        t.manufacturer = $manufacturer,
                        t.model = $model
                    MERGE (s)-[:SUPPLIES {cable_id: $cable_id}]->(t)
                    """,
                    substation_id=substation_id,
                    asset_id=asset_id,
                    rating=random.choice([250, 400, 630, 800]),
                    manufacturer=random.choice(["ABB", "Siemens", "Schneider"]),
                    model=f"GRID-{transformer_number:03d}",
                    cable_id=f"CB_{transformer_number:03d}",
                )

                for m in range(1, 6):
                    meter_number = ((transformer_number - 1) * 5) + m
                    meter_id = f"SM_{meter_number:05d}"
                    session.run(
                        """
                        MATCH (t:Transformer {asset_id: $asset_id})
                        MERGE (m:SmartMeter {meter_id: $meter_id})
                        SET m.node_id = $meter_id,
                            m.premise_id = $premise_id,
                            m.tariff_class = $tariff_class,
                            m.phase = $phase
                        MERGE (t)-[:CONNECTS_TO]->(m)
                        """,
                        asset_id=asset_id,
                        meter_id=meter_id,
                        premise_id=f"PREM_{10000 + meter_number}",
                        tariff_class="commercial" if meter_number % 7 == 0 else "residential",
                        phase="three" if meter_number % 7 == 0 else "single",
                    )
    driver.close()
    print("Seeded Neo4j: 10 substations, 40 transformers, 200 smart meters.")


def seed_mongo(env: dict[str, str]) -> None:
    host = reachable_host(env.get("MONGO_HOST", "catalog-db"))
    client = MongoClient(
        host=host,
        port=int(env.get("MONGO_PORT", "27017")),
        username=env["MONGO_INITDB_ROOT_USERNAME"],
        password=env["MONGO_INITDB_ROOT_PASSWORD"],
        authSource="admin",
    )
    db = client[env.get("MONGO_INITDB_DATABASE", "gridsense_catalog")]
    db.equipment.create_index("equipment_id", unique=True)

    records = []
    for i in range(1, 11):
        records.append(
            {
                "equipment_id": f"TX_{i:03d}",
                "type": "transformer",
                "manufacturer": random.choice(["ABB", "Siemens", "Schneider"]),
                "rated_kva": random.choice([250, 400, 630]),
                "telemetry": {"oil_temperature": True, "load_percent": True},
                f"vendor_transformer_metric_{i:02d}": round(0.1 * i, 3),
            }
        )
    for i in range(1, 11):
        records.append(
            {
                "equipment_id": f"SW_{i:03d}",
                "type": "switchgear",
                "manufacturer": random.choice(["Schneider", "Eaton", "ABB"]),
                "interrupting_capacity_ka": random.choice([16, 20, 25]),
                "feeder_id": f"F_{i:03d}",
                "maintenance": {"operation_count": i * 37},
                f"switchgear_option_{i:02d}": {"enabled": i % 2 == 0},
            }
        )
    for i in range(1, 11):
        telemetry_fields = [f"vendor_field_{n:02d}" for n in range(1, 41)]
        records.append(
            {
                "equipment_id": f"SM_META_{i:03d}",
                "type": "smart_meter",
                "manufacturer": random.choice(["Itron", "Landis+Gyr", "Kamstrup"]),
                "transformer_id": f"TX_{((i - 1) % 10) + 1:03d}",
                "telemetry_fields": telemetry_fields,
                "firmware": {"major": 2, "minor": i},
                f"meter_vendor_extension_{i:02d}": telemetry_fields[:i],
            }
        )

    for record in records:
        db.equipment.update_one(
            {"equipment_id": record["equipment_id"]},
            {"$set": record},
            upsert=True,
        )
    client.close()
    print("Seeded MongoDB: 30 heterogeneous equipment records.")


def deterministic_uuid(value: str) -> str:
    return str(uuid5(NAMESPACE_DNS, value))


async def seed_postgres(env: dict[str, str]) -> None:
    host = reachable_host(env.get("POSTGRES_HOST", "billing-db"))
    conn = await asyncpg.connect(
        host=host,
        port=int(env.get("POSTGRES_PORT", "5432")),
        database=env.get("POSTGRES_DB", "gridsense_billing"),
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
    )
    try:
        async with conn.transaction():
            for i in range(1, 101):
                customer_id = deterministic_uuid(f"customer-{i}")
                premise_id = deterministic_uuid(f"premise-{i}")
                email = f"customer{i:03d}@example.com"
                await conn.execute(
                    """
                    INSERT INTO customers (customer_id, full_name, email)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name
                    """,
                    customer_id,
                    f"Customer {i:03d}",
                    email,
                )
                await conn.execute(
                    """
                    INSERT INTO premises (
                        premise_id, customer_id, address, district, transformer_id
                    )
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (premise_id) DO NOTHING
                    """,
                    premise_id,
                    customer_id,
                    f"{i} Grid Avenue",
                    f"DISTRICT_{((i - 1) % 5) + 1:02d}",
                    f"TX_{((i - 1) % 40) + 1:03d}",
                )
                await conn.execute(
                    """
                    INSERT INTO bills (
                        premise_id, billing_month, total_kwh, total_amount, status
                    )
                    VALUES ($1, DATE '2026-04-01', $2, $3, 'ISSUED')
                    ON CONFLICT (premise_id, billing_month) DO NOTHING
                    """,
                    premise_id,
                    Decimal("180.0") + Decimal(i),
                    Decimal("35.00") + Decimal(i) / Decimal("10"),
                )
    finally:
        await conn.close()
    print("Seeded PostgreSQL: 100 accounts with invoice records.")


def main() -> None:
    env = load_env()
    required = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "MONGO_INITDB_ROOT_USERNAME",
        "MONGO_INITDB_ROOT_PASSWORD",
        "NEO4J_PASSWORD",
    ]
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise SystemExit(f"Missing required environment values: {', '.join(missing)}")

    seed_cassandra(env)
    seed_neo4j(env)
    seed_mongo(env)
    asyncio.run(seed_postgres(env))


if __name__ == "__main__":
    main()
