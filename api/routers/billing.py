from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Query, status

from db.postgres import get_pool
from models.postgres import (
    Bill,
    BillCreate,
    BillingAccount,
    Customer,
    InvoiceCreate,
    Tariff,
)

router = APIRouter(prefix="/billing", tags=["billing"])

LimitQuery = Annotated[int, Query(ge=1, le=200)]


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calculate_amount(total_kwh: Decimal, tariff_rules: dict) -> Decimal:
    remaining = Decimal(total_kwh)
    previous_limit = Decimal("0")
    energy_amount = Decimal("0")

    for band in tariff_rules.get("bands", []):
        raw_limit = band.get("up_to_kwh")
        price = Decimal(str(band["price_per_kwh"]))
        if raw_limit is None:
            band_kwh = remaining
        else:
            limit = Decimal(str(raw_limit))
            band_kwh = min(remaining, max(limit - previous_limit, Decimal("0")))
            previous_limit = limit

        if band_kwh <= 0:
            continue
        energy_amount += band_kwh * price
        remaining -= band_kwh
        if remaining <= 0:
            break

    fixed_fee = Decimal(str(tariff_rules.get("fixed_monthly_fee", 0)))
    surcharge_percent = Decimal(str(tariff_rules.get("regulatory_surcharge_percent", 0)))
    subtotal = energy_amount + fixed_fee
    return _money(subtotal * (Decimal("1") + surcharge_percent / Decimal("100")))


@router.get("/customers", response_model=list[Customer])
async def list_customers(limit: LimitQuery = 50):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT customer_id, full_name, email, created_at
            FROM customers
            ORDER BY created_at DESC, full_name ASC
            LIMIT $1
            """,
            limit,
        )
    return [dict(row) for row in rows]


@router.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: UUID):
    pool = await get_pool()
    async with pool.acquire() as conn:
        customer = await conn.fetchrow(
            """
            SELECT customer_id, full_name, email, created_at
            FROM customers
            WHERE customer_id = $1
            """,
            customer_id,
        )
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )
    return dict(customer)


@router.get("/tariffs", response_model=list[Tariff])
async def list_tariffs():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT tariff_id, name, tariff_rules AS rules, active
            FROM tariffs
            WHERE active = TRUE
            ORDER BY name ASC
            """
        )
    return [dict(row) for row in rows]


@router.get("/bills", response_model=list[Bill])
async def list_bills(limit: LimitQuery = 50, customer_id: UUID | None = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                b.bill_id,
                p.customer_id,
                b.premise_id,
                b.billing_month,
                b.total_kwh,
                b.total_amount,
                b.status,
                b.created_at
            FROM bills b
            JOIN premises p ON p.premise_id = b.premise_id
            WHERE ($1::uuid IS NULL OR p.customer_id = $1)
            ORDER BY b.created_at DESC, b.billing_month DESC
            LIMIT $2
            """,
            customer_id,
            limit,
        )
    return [dict(row) for row in rows]


@router.get("/bills/{bill_id}", response_model=Bill)
async def get_bill(bill_id: UUID):
    pool = await get_pool()
    async with pool.acquire() as conn:
        bill = await conn.fetchrow(
            """
            SELECT
                b.bill_id,
                p.customer_id,
                b.premise_id,
                b.billing_month,
                b.total_kwh,
                b.total_amount,
                b.status,
                b.created_at
            FROM bills b
            JOIN premises p ON p.premise_id = b.premise_id
            WHERE b.bill_id = $1
            """,
            bill_id,
        )
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found.",
        )
    return dict(bill)


@router.post("/bills", response_model=Bill, status_code=status.HTTP_201_CREATED)
async def create_bill(bill: BillCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    WITH inserted AS (
                        INSERT INTO bills (
                            premise_id,
                            billing_month,
                            total_kwh,
                            total_amount,
                            status
                        )
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING
                            bill_id,
                            premise_id,
                            billing_month,
                            total_kwh,
                            total_amount,
                            status,
                            created_at
                    )
                    SELECT
                        inserted.bill_id,
                        p.customer_id,
                        inserted.premise_id,
                        inserted.billing_month,
                        inserted.total_kwh,
                        inserted.total_amount,
                        inserted.status,
                        inserted.created_at
                    FROM inserted
                    JOIN premises p ON p.premise_id = inserted.premise_id
                    """,
                    bill.premise_id,
                    bill.billing_month,
                    bill.total_kwh,
                    bill.total_amount,
                    bill.status,
                )
        except asyncpg.UniqueViolationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A bill already exists for this premise and billing month.",
            ) from exc
        except asyncpg.ForeignKeyViolationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Premise does not exist.",
            ) from exc
        except asyncpg.CheckViolationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bill violates database constraints.",
            ) from exc
    return dict(row)


@router.get("/account/{premise_id}", response_model=BillingAccount)
async def get_billing_account(premise_id: UUID):
    pool = await get_pool()
    async with pool.acquire() as conn:
        account = await conn.fetchrow(
            """
            SELECT
                p.premise_id,
                c.customer_id,
                c.full_name,
                c.email,
                p.address,
                p.district,
                p.transformer_id,
                COALESCE(
                    SUM(
                        CASE
                            WHEN b.status IN ('ISSUED', 'DRAFT') THEN b.total_amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS current_balance
            FROM premises p
            JOIN customers c ON c.customer_id = p.customer_id
            LEFT JOIN bills b ON b.premise_id = p.premise_id
            WHERE p.premise_id = $1
            GROUP BY p.premise_id, c.customer_id
            """,
            premise_id,
        )
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Billing account not found.",
            )

        bills = await conn.fetch(
            """
            SELECT
                b.bill_id,
                p.customer_id,
                b.premise_id,
                b.billing_month,
                b.total_kwh,
                b.total_amount,
                b.status,
                b.created_at
            FROM bills b
            JOIN premises p ON p.premise_id = b.premise_id
            WHERE b.premise_id = $1
            ORDER BY b.billing_month DESC, b.created_at DESC
            """,
            premise_id,
        )

    result = dict(account)
    result["bills"] = [dict(row) for row in bills]
    return result


@router.post("/invoice", response_model=Bill, status_code=status.HTTP_201_CREATED)
async def create_invoice(invoice: InvoiceCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                premise = await conn.fetchrow(
                    """
                    SELECT p.premise_id
                    FROM premises p
                    WHERE p.premise_id = $1
                    FOR UPDATE
                    """,
                    invoice.premise_id,
                )
                if premise is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Premise does not exist.",
                    )

                tariff = await conn.fetchrow(
                    """
                    SELECT tariff_rules
                    FROM tariffs
                    WHERE active = TRUE
                      AND ($1::text IS NULL OR name = $1)
                    ORDER BY name
                    LIMIT 1
                    """,
                    invoice.tariff_name,
                )
                if tariff is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No active tariff matched invoice.",
                    )

                total_amount = _calculate_amount(
                    invoice.total_kwh,
                    tariff["tariff_rules"],
                )
                row = await conn.fetchrow(
                    """
                    WITH inserted AS (
                        INSERT INTO bills (
                            premise_id,
                            billing_month,
                            total_kwh,
                            total_amount,
                            status
                        )
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING
                            bill_id,
                            premise_id,
                            billing_month,
                            total_kwh,
                            total_amount,
                            status,
                            created_at
                    )
                    SELECT
                        inserted.bill_id,
                        p.customer_id,
                        inserted.premise_id,
                        inserted.billing_month,
                        inserted.total_kwh,
                        inserted.total_amount,
                        inserted.status,
                        inserted.created_at
                    FROM inserted
                    JOIN premises p ON p.premise_id = inserted.premise_id
                    """,
                    invoice.premise_id,
                    invoice.billing_month,
                    invoice.total_kwh,
                    total_amount,
                    invoice.status,
                )
        except asyncpg.UniqueViolationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A bill already exists for this premise and billing month.",
            ) from exc
        except asyncpg.ForeignKeyViolationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Premise does not exist.",
            ) from exc
        except asyncpg.CheckViolationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice violates database constraints.",
            ) from exc
    return dict(row)
