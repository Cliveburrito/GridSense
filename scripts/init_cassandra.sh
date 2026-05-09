#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CASSANDRA_CONTAINER_NAME:-gridsense_cassandra}"
CQL_FILE_IN_CONTAINER="${CQL_FILE_IN_CONTAINER:-/docker-entrypoint-initdb.d/init.cql}"
MAX_RETRIES="${MAX_RETRIES:-30}"
SLEEP_SECONDS="${SLEEP_SECONDS:-5}"

echo "Waiting for Cassandra container: ${CONTAINER_NAME}"

for attempt in $(seq 1 "$MAX_RETRIES"); do
  if podman exec "$CONTAINER_NAME" cqlsh -e "DESCRIBE KEYSPACES;" >/dev/null 2>&1; then
    echo "Cassandra is ready."
    break
  fi

  if [ "$attempt" -eq "$MAX_RETRIES" ]; then
    echo "Cassandra did not become ready after ${MAX_RETRIES} attempts."
    exit 1
  fi

  echo "Cassandra not ready yet. Attempt ${attempt}/${MAX_RETRIES}. Retrying in ${SLEEP_SECONDS}s..."
  sleep "$SLEEP_SECONDS"
done

echo "Applying Cassandra schema from ${CQL_FILE_IN_CONTAINER}"
podman exec "$CONTAINER_NAME" cqlsh -f "$CQL_FILE_IN_CONTAINER"

echo "Verifying gridsense keyspace"
podman exec "$CONTAINER_NAME" cqlsh -e "DESCRIBE KEYSPACE gridsense;"

echo "Cassandra schema initialized successfully."