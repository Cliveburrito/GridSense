// neo4j/import/seed.cypher

// Constraints
CREATE CONSTRAINT gsp_id IF NOT EXISTS
FOR (g:GridSupplyPoint) REQUIRE g.gsp_id IS UNIQUE;

CREATE CONSTRAINT substation_id IF NOT EXISTS
FOR (s:Substation) REQUIRE s.substation_id IS UNIQUE;

CREATE CONSTRAINT transformer_id IF NOT EXISTS
FOR (t:Transformer) REQUIRE t.asset_id IS UNIQUE;

CREATE CONSTRAINT meter_id IF NOT EXISTS
FOR (m:SmartMeter) REQUIRE m.meter_id IS UNIQUE;


// Nodes

MERGE (:GridSupplyPoint {
  gsp_id: "GSP_NORTH",
  name: "Northern Grid Supply Point",
  voltage_kV: 132,
  region: "North Metro"
});

MERGE (:Substation {
  substation_id: "SS_001",
  name: "Volos Primary",
  voltage_kV: 11,
  lat: 39.358,
  lon: 22.938,
  commissioned_year: 1998
});

MERGE (:Substation {
  substation_id: "SS_002",
  name: "Nea Ionia Secondary",
  voltage_kV: 11,
  lat: 39.379,
  lon: 22.927,
  commissioned_year: 2006
});

MERGE (:Transformer {
  asset_id: "TX_001_A",
  rating_kVA: 400,
  manufacturer: "ABB",
  model: "ONAN-400",
  installed: date("2012-06-15"),
  last_inspection: date("2024-09-01")
});

MERGE (:Transformer {
  asset_id: "TX_002_B",
  rating_kVA: 630,
  manufacturer: "Siemens",
  model: "S-630",
  installed: date("2016-03-20"),
  last_inspection: date("2024-07-18")
});

MERGE (:Transformer {
  asset_id: "TX_003_C",
  rating_kVA: 250,
  manufacturer: "Schneider",
  model: "Eco-250",
  installed: date("2019-11-05"),
  last_inspection: date("2024-08-11")
});

MERGE (:SmartMeter {
  meter_id: "SM_00001",
  premise_id: "PREM_10001",
  tariff_class: "residential",
  phase: "single"
});

MERGE (:SmartMeter {
  meter_id: "SM_00002",
  premise_id: "PREM_10002",
  tariff_class: "residential",
  phase: "single"
});

MERGE (:SmartMeter {
  meter_id: "SM_00003",
  premise_id: "PREM_10003",
  tariff_class: "commercial",
  phase: "three"
});

MERGE (:SmartMeter {
  meter_id: "SM_00004",
  premise_id: "PREM_10004",
  tariff_class: "residential",
  phase: "single"
});

MERGE (:SmartMeter {
  meter_id: "SM_00005",
  premise_id: "PREM_10005",
  tariff_class: "commercial",
  phase: "three"
});

MERGE (:SmartMeter {
  meter_id: "SM_00006",
  premise_id: "PREM_10006",
  tariff_class: "residential",
  phase: "single"
});

MERGE (:SmartMeter {
  meter_id: "SM_00007",
  premise_id: "PREM_10007",
  tariff_class: "residential",
  phase: "single"
});

MERGE (:SmartMeter {
  meter_id: "SM_00008",
  premise_id: "PREM_10008",
  tariff_class: "commercial",
  phase: "three"
});

MERGE (:SmartMeter {
  meter_id: "SM_00009",
  premise_id: "PREM_10009",
  tariff_class: "residential",
  phase: "single"
});

MERGE (:SmartMeter {
  meter_id: "SM_00010",
  premise_id: "PREM_10010",
  tariff_class: "residential",
  phase: "single"
});

MERGE (:SmartMeter {
  meter_id: "SM_00011",
  premise_id: "PREM_10011",
  tariff_class: "residential",
  phase: "single"
});

MERGE (:SmartMeter {
  meter_id: "SM_00012",
  premise_id: "PREM_10012",
  tariff_class: "commercial",
  phase: "three"
});

MERGE (:SmartMeter {
  meter_id: "SM_00013",
  premise_id: "PREM_10013",
  tariff_class: "residential",
  phase: "single"
});

MERGE (:SmartMeter {
  meter_id: "SM_00014",
  premise_id: "PREM_10014",
  tariff_class: "residential",
  phase: "single"
});


// Relationships

MATCH (g:GridSupplyPoint {gsp_id: "GSP_NORTH"})
MATCH (s:Substation {substation_id: "SS_001"})
MERGE (g)-[:FEEDS {
  feeder_id: "F_001",
  voltage_kV: 11,
  length_km: 2.4,
  impedance_ohm: 0.42
}]->(s);

MATCH (g:GridSupplyPoint {gsp_id: "GSP_NORTH"})
MATCH (s:Substation {substation_id: "SS_002"})
MERGE (g)-[:FEEDS {
  feeder_id: "F_002",
  voltage_kV: 11,
  length_km: 3.1,
  impedance_ohm: 0.55
}]->(s);

MATCH (s:Substation {substation_id: "SS_001"})
MATCH (t:Transformer {asset_id: "TX_001_A"})
MERGE (s)-[:SUPPLIES {
  cable_id: "CB_001",
  distance_m: 320,
  phase: "ABC"
}]->(t);

MATCH (s:Substation {substation_id: "SS_001"})
MATCH (t:Transformer {asset_id: "TX_002_B"})
MERGE (s)-[:SUPPLIES {
  cable_id: "CB_002",
  distance_m: 510,
  phase: "ABC"
}]->(t);

MATCH (s:Substation {substation_id: "SS_002"})
MATCH (t:Transformer {asset_id: "TX_003_C"})
MERGE (s)-[:SUPPLIES {
  cable_id: "CB_003",
  distance_m: 280,
  phase: "ABC"
}]->(t);

MATCH (t:Transformer {asset_id: "TX_001_A"})
MATCH (m:SmartMeter {meter_id: "SM_00001"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 18}]->(m);

MATCH (t:Transformer {asset_id: "TX_001_A"})
MATCH (m:SmartMeter {meter_id: "SM_00002"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 25}]->(m);

MATCH (t:Transformer {asset_id: "TX_001_A"})
MATCH (m:SmartMeter {meter_id: "SM_00003"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 30}]->(m);

MATCH (t:Transformer {asset_id: "TX_001_A"})
MATCH (m:SmartMeter {meter_id: "SM_00004"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 21}]->(m);

MATCH (t:Transformer {asset_id: "TX_002_B"})
MATCH (m:SmartMeter {meter_id: "SM_00005"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 19}]->(m);

MATCH (t:Transformer {asset_id: "TX_002_B"})
MATCH (m:SmartMeter {meter_id: "SM_00006"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 26}]->(m);

MATCH (t:Transformer {asset_id: "TX_002_B"})
MATCH (m:SmartMeter {meter_id: "SM_00007"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 14}]->(m);

MATCH (t:Transformer {asset_id: "TX_002_B"})
MATCH (m:SmartMeter {meter_id: "SM_00008"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 22}]->(m);

MATCH (t:Transformer {asset_id: "TX_003_C"})
MATCH (m:SmartMeter {meter_id: "SM_00009"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 23}]->(m);

MATCH (t:Transformer {asset_id: "TX_003_C"})
MATCH (m:SmartMeter {meter_id: "SM_00010"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 29}]->(m);

MATCH (t:Transformer {asset_id: "TX_003_C"})
MATCH (m:SmartMeter {meter_id: "SM_00011"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 15}]->(m);

MATCH (t:Transformer {asset_id: "TX_003_C"})
MATCH (m:SmartMeter {meter_id: "SM_00012"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 33}]->(m);

MATCH (t:Transformer {asset_id: "TX_003_C"})
MATCH (m:SmartMeter {meter_id: "SM_00013"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 28}]->(m);

MATCH (t:Transformer {asset_id: "TX_003_C"})
MATCH (m:SmartMeter {meter_id: "SM_00014"})
MERGE (t)-[:CONNECTS_TO {service_line_m: 17}]->(m);