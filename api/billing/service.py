from uuid import UUID

from billing import repository
from billing.schemas import BillCreate


def list_customers(limit: int) -> list[dict]:
    return repository.list_customers(limit=limit)


def get_customer(customer_id: UUID) -> dict | None:
    return repository.get_customer(customer_id=customer_id)


def list_tariffs() -> list[dict]:
    return repository.list_tariffs()


def list_bills(limit: int, customer_id: UUID | None = None) -> list[dict]:
    return repository.list_bills(limit=limit, customer_id=customer_id)


def get_bill(bill_id: UUID) -> dict | None:
    return repository.get_bill(bill_id=bill_id)


def create_bill(bill: BillCreate) -> dict:
    return repository.create_bill(bill=bill)
