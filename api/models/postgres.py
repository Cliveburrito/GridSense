from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


BillStatus = Literal["DRAFT", "ISSUED", "PAID", "CANCELLED"]


class Customer(BaseModel):
    customer_id: UUID
    full_name: str
    email: str
    created_at: datetime


class Tariff(BaseModel):
    tariff_id: UUID
    name: str
    rules: dict[str, Any]
    active: bool


class Bill(BaseModel):
    bill_id: UUID
    customer_id: UUID
    premise_id: UUID
    billing_month: date
    total_kwh: Decimal
    total_amount: Decimal
    status: BillStatus
    created_at: datetime

    model_config = ConfigDict(json_encoders={Decimal: str})


class BillCreate(BaseModel):
    premise_id: UUID
    billing_month: date
    total_kwh: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    total_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    status: BillStatus


class InvoiceCreate(BaseModel):
    premise_id: UUID
    billing_month: date
    total_kwh: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    tariff_name: str | None = None
    status: BillStatus = "ISSUED"


class BillingAccount(BaseModel):
    premise_id: UUID
    customer_id: UUID
    full_name: str
    email: str
    address: str
    district: str
    transformer_id: str
    current_balance: Decimal
    bills: list[Bill]

    model_config = ConfigDict(json_encoders={Decimal: str})
