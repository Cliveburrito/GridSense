CREATE KEYSPACE IF NOT EXISTS gridsense
WITH replication = {
  'class': 'SimpleStrategy',
  'replication_factor': 1
};

USE gridsense;

CREATE TABLE IF NOT EXISTS sensor_readings (
  sensor_id TEXT,
  reading_time TIMESTAMP,
  metric_type TEXT,
  value FLOAT,
  unit TEXT,
  quality_flag TINYINT,
  PRIMARY KEY ((sensor_id), reading_time)
) WITH CLUSTERING ORDER BY (reading_time DESC)
AND default_time_to_live = 7776000;

CREATE TABLE IF NOT EXISTS relay_events (
  feeder_id TEXT,
  event_time TIMEUUID,
  relay_id TEXT,
  event_type TEXT,
  fault_type TEXT,
  current_kA FLOAT,
  PRIMARY KEY ((feeder_id), event_time)
) WITH CLUSTERING ORDER BY (event_time ASC);

-- Extra table for dashboard query pattern:
-- recent readings across the network by time bucket and district.
CREATE TABLE IF NOT EXISTS sensor_readings_by_bucket (
  bucket_minute TEXT,
  district_id TEXT,
  metric_type TEXT,
  reading_time TIMESTAMP,
  sensor_id TEXT,
  value FLOAT,
  unit TEXT,
  quality_flag TINYINT,
  PRIMARY KEY ((bucket_minute, district_id, metric_type), reading_time, sensor_id)
) WITH CLUSTERING ORDER BY (reading_time DESC)
AND default_time_to_live = 7776000;