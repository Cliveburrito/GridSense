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