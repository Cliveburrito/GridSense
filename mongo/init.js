db = db.getSiblingDB("gridsense_catalog");

if (!db.getCollectionNames().includes("equipment")) {
  db.createCollection("equipment");
}

db.equipment.createIndex({ equipment_id: 1 }, { unique: true });
db.equipment.createIndex({ type: 1 });
db.equipment.createIndex({ manufacturer: 1 });
db.equipment.createIndex({ transformer_id: 1 });

const equipmentSeed = [
  {
    equipment_id: "TX_001_A",
    type: "transformer",
    manufacturer: "ABB",
    model: "ONAN-400",
    installed: new Date("2012-06-15"),
    last_inspection: new Date("2024-09-01"),
    rated_kva: 400,
    cooling: "ONAN",
    telemetry: {
      oil_temperature: true,
      winding_temperature: true,
      load_percent: true
    },
    protection: {
      relay_model: "ABB REF615",
      firmware: "5.1.2"
    }
  },
  {
    equipment_id: "TX_002_B",
    type: "transformer",
    manufacturer: "Siemens",
    model: "S-630",
    installed: new Date("2016-03-20"),
    last_inspection: new Date("2024-07-18"),
    rated_kva: 630,
    cooling: "ONAF",
    telemetry: {
      oil_temperature: true,
      winding_temperature: true,
      dissolved_gas_analysis: true,
      vibration: true
    },
    protection: {
      relay_model: "Siemens 7SJ82",
      firmware: "8.3"
    },
    manufacturer_specific: {
      thermal_ageing_index: 0.18,
      fan_stage_count: 2
    }
  },
  {
    equipment_id: "SM_00001",
    type: "smart_meter",
    manufacturer: "Landis+Gyr",
    model: "E450",
    premise_id: "PREM_10001",
    transformer_id: "TX_001_A",
    phase: "single",
    telemetry_fields: ["voltage", "current", "power_factor", "energy_kwh"]
  },
  {
    equipment_id: "SM_00003",
    type: "smart_meter",
    manufacturer: "Itron",
    model: "ACE6000",
    premise_id: "PREM_10003",
    transformer_id: "TX_001_A",
    phase: "three",
    telemetry_fields: [
      "voltage_l1",
      "voltage_l2",
      "voltage_l3",
      "current_l1",
      "current_l2",
      "current_l3",
      "power_factor",
      "energy_kwh",
      "tamper_alarm"
    ],
    manufacturer_specific: {
      remote_disconnect: true,
      event_log_depth: 2048
    }
  },
  {
    equipment_id: "SW_001",
    type: "switchgear",
    manufacturer: "Schneider",
    model: "RM6",
    feeder_id: "F_001",
    rated_voltage_kv: 11,
    interrupting_capacity_ka: 16,
    telemetry: {
      position: true,
      operation_count: true,
      cabinet_temperature: true
    }
  }
];

equipmentSeed.forEach((equipment) => {
  db.equipment.updateOne(
    { equipment_id: equipment.equipment_id },
    { $set: equipment },
    { upsert: true }
  );
});
