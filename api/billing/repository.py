from uuid import UUID

from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

from billing.schemas import BillCreate
from db.postgres import get_connection


class BillingRepositoryError(Exception):
    pass


class DuplicateBillError(BillingRepositoryError):
    pass


class InvalidBillReferenceError(BillingRepositoryError):
    pass


class InvalidBillValueError(BillingRepositoryError):
    pass


def list_customers(limit: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT customer_id, full_name, email, created_at
                FROM customers
                ORDER BY created_at DESC, full_name ASC
                LIMIT %(limit)s
                """,
                {"limit": limit},
            )
            return list(cur.fetchall())


def get_customer(customer_id: UUID) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT customer_id, full_name, email, created_at
                FROM customers
                WHERE customer_id = %(customer_id)s
                """,
                {"customer_id": customer_id},
            )
            return cur.fetchone()


def list_tariffs() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tariff_id, name, tariff_rules AS rules, active
                FROM tariffs
                WHERE active = TRUE
                ORDER BY name ASC
                """
            )
            return list(cur.fetchall())


def list_bills(limit: int, customer_id: UUID | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
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
                WHERE (
                    %(customer_id)s::uuid IS NULL
                    OR p.customer_id = %(customer_id)s
                )
                ORDER BY b.created_at DESC, b.billing_month DESC
                LIMIT %(limit)s
                """,
                {"limit": limit, "customer_id": customer_id},
            )
            return list(cur.fetchall())


def get_bill(bill_id: UUID) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
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
                WHERE b.bill_id = %(bill_id)s
                """,
                {"bill_id": bill_id},
            )
            return cur.fetchone()


def create_bill(bill: BillCreate) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    WITH inserted AS (
                        INSERT INTO bills (
                            premise_id,
                            billing_month,
                            total_kwh,
                            total_amount,
                            status
                        )
                        VALUES (
                            %(premise_id)s,
                            %(billing_month)s,
                            %(total_kwh)s,
                            %(total_amount)s,
                            %(status)s
                        )
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
                    bill.model_dump(),
                )
                return cur.fetchone()
            except UniqueViolation as exc:
                raise DuplicateBillError(
                    "A bill already exists for this premise and billing month."
                ) from exc
            except ForeignKeyViolation as exc:
                raise InvalidBillReferenceError("Premise does not exist.") from exc
            except CheckViolation as exc:
                raise InvalidBillValueError("Bill violates database constraints.") from exc
