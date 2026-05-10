from __future__ import annotations

import os
import random
import socket
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid5, NAMESPACE_DNS

import psycopg
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


def bucket_minute(reading_time: datetime) -> str:
    return reading_time.astimezone(timezone.utc).strftime("%Y%m%d%H%M")


def seed_cassandra(env: dict[str, str]) -> None:
    host = reachable_host(env.get("CASSANDRA_HOST", "localhost"))
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

    start = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=2)
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
    uri = env.get("NEO4J_URI", "bolt://localhost:7687")
    if "graph-db" in uri:
        uri = uri.replace("graph-db", "localhost")
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
    host = reachable_host(env.get("MONGO_HOST", "localhost"))
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


def seed_postgres(env: dict[str, str]) -> None:
    host = reachable_host(env.get("POSTGRES_HOST", "localhost"))
    with psycopg.connect(
        host=host,
        port=int(env.get("POSTGRES_PORT", "5432")),
        dbname=env.get("POSTGRES_DB", "gridsense_billing"),
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
    ) as conn:
        with conn.cursor() as cur:
            for i in range(1, 101):
                customer_id = deterministic_uuid(f"customer-{i}")
                premise_id = deterministic_uuid(f"premise-{i}")
                email = f"customer{i:03d}@example.com"
                cur.execute(
                    """
                    INSERT INTO customers (customer_id, full_name, email)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name
                    """,
                    (customer_id, f"Customer {i:03d}", email),
                )
                cur.execute(
                    """
                    INSERT INTO premises (
                        premise_id, customer_id, address, district, transformer_id
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (premise_id) DO NOTHING
                    """,
                    (
                        premise_id,
                        customer_id,
                        f"{i} Grid Avenue",
                        f"DISTRICT_{((i - 1) % 5) + 1:02d}",
                        f"TX_{((i - 1) % 40) + 1:03d}",
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO bills (
                        premise_id, billing_month, total_kwh, total_amount, status
                    )
                    VALUES (%s, DATE '2026-04-01', %s, %s, 'ISSUED')
                    ON CONFLICT (premise_id, billing_month) DO NOTHING
                    """,
                    (
                        premise_id,
                        Decimal("180.0") + Decimal(i),
                        Decimal("35.00") + Decimal(i) / Decimal("10"),
                    ),
                )
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
    seed_postgres(env)


if __name__ == "__main__":
    main()
