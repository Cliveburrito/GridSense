from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from billing import repository, service
from billing.schemas import Bill, BillCreate, Customer, Tariff

router = APIRouter(prefix="/billing", tags=["billing"])

LimitQuery = Annotated[int, Query(ge=1, le=200)]


@router.get("/customers", response_model=list[Customer])
def list_customers(limit: LimitQuery = 50):
    return service.list_customers(limit=limit)


@router.get("/customers/{customer_id}", response_model=Customer)
def get_customer(customer_id: UUID):
    customer = service.get_customer(customer_id=customer_id)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )
    return customer


@router.get("/tariffs", response_model=list[Tariff])
def list_tariffs():
    return service.list_tariffs()


@router.get("/bills", response_model=list[Bill])
def list_bills(limit: LimitQuery = 50, customer_id: UUID | None = None):
    return service.list_bills(limit=limit, customer_id=customer_id)


@router.get("/bills/{bill_id}", response_model=Bill)
def get_bill(bill_id: UUID):
    bill = service.get_bill(bill_id=bill_id)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found.",
        )
    return bill


@router.post("/bills", response_model=Bill, status_code=status.HTTP_201_CREATED)
def create_bill(bill: BillCreate):
    try:
        return service.create_bill(bill=bill)
    except (
        repository.DuplicateBillError,
        repository.InvalidBillReferenceError,
        repository.InvalidBillValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/account/{premise_id}")
def get_billing_account(premise_id: UUID):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Billing account balance endpoint is planned for the invoice implementation pass.",
    )


@router.post("/invoice")
def create_invoice(invoice: dict):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Monthly invoice generation is planned for the invoice implementation pass.",
    )
