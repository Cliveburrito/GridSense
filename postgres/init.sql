CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS customers (
    customer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS premises (
    premise_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(customer_id),
    address TEXT NOT NULL,
    district TEXT NOT NULL,
    transformer_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tariffs (
    tariff_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    tariff_rules JSONB NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS bills (
    bill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    premise_id UUID NOT NULL REFERENCES premises(premise_id),
    billing_month DATE NOT NULL,
    total_kwh NUMERIC(12, 3) NOT NULL CHECK (total_kwh >= 0),
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    status TEXT NOT NULL CHECK (status IN ('DRAFT', 'ISSUED', 'PAID', 'CANCELLED')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (premise_id, billing_month)
);

CREATE INDEX IF NOT EXISTS idx_premises_customer_id ON premises(customer_id);
CREATE INDEX IF NOT EXISTS idx_premises_transformer_id ON premises(transformer_id);
CREATE INDEX IF NOT EXISTS idx_bills_premise_id ON bills(premise_id);
CREATE INDEX IF NOT EXISTS idx_bills_billing_month ON bills(billing_month);
CREATE INDEX IF NOT EXISTS idx_tariffs_rules_gin ON tariffs USING GIN (tariff_rules);

INSERT INTO customers (full_name, email)
VALUES
    ('Maria Nikolaou', 'maria.nikolaou@example.com'),
    ('Nikos Papadopoulos', 'nikos.papadopoulos@example.com')
ON CONFLICT (email) DO NOTHING;

INSERT INTO premises (customer_id, address, district, transformer_id)
SELECT
    c.customer_id,
    '12 Egnatia Street',
    'Thessaloniki Center',
    'TX_001_A'
FROM customers c
WHERE c.email = 'maria.nikolaou@example.com'
  AND NOT EXISTS (
      SELECT 1
      FROM premises p
      WHERE p.customer_id = c.customer_id
        AND p.address = '12 Egnatia Street'
  );

INSERT INTO premises (customer_id, address, district, transformer_id)
SELECT
    c.customer_id,
    '48 Tsimiski Avenue',
    'Thessaloniki Center',
    'TX_002_B'
FROM customers c
WHERE c.email = 'nikos.papadopoulos@example.com'
  AND NOT EXISTS (
      SELECT 1
      FROM premises p
      WHERE p.customer_id = c.customer_id
        AND p.address = '48 Tsimiski Avenue'
  );

INSERT INTO tariffs (name, tariff_rules)
VALUES
    (
        'Residential Standard',
        '{
          "type": "progressive",
          "currency": "EUR",
          "bands": [
            {"up_to_kwh": 100, "price_per_kwh": 0.12},
            {"up_to_kwh": 300, "price_per_kwh": 0.18},
            {"up_to_kwh": null, "price_per_kwh": 0.24}
          ],
          "fixed_monthly_fee": 5.00,
          "regulatory_surcharge_percent": 6.5
        }'::jsonb
    )
ON CONFLICT (name) DO NOTHING;

INSERT INTO bills (premise_id, billing_month, total_kwh, total_amount, status)
SELECT
    p.premise_id,
    DATE '2026-04-01',
    245.750,
    49.15,
    'ISSUED'
FROM premises p
JOIN customers c ON c.customer_id = p.customer_id
WHERE c.email = 'maria.nikolaou@example.com'
  AND p.address = '12 Egnatia Street'
ON CONFLICT (premise_id, billing_month) DO NOTHING;
