from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from equipment import repository, service
from equipment.schemas import EquipmentDocument

router = APIRouter(prefix="/equipment", tags=["equipment"])

LimitQuery = Annotated[int, Query(ge=1, le=200)]


@router.get("", response_model=list[EquipmentDocument])
def list_equipment(
    limit: LimitQuery = 50,
    equipment_type: Annotated[str | None, Query(alias="type")] = None,
    manufacturer: str | None = None,
):
    return service.list_equipment(
        limit=limit,
        equipment_type=equipment_type,
        manufacturer=manufacturer,
    )


@router.get("/type/{equipment_type}", response_model=list[EquipmentDocument])
def list_equipment_by_type(equipment_type: str, limit: LimitQuery = 50):
    return service.list_equipment_by_type(
        equipment_type=equipment_type,
        limit=limit,
    )


@router.get("/transformer/{transformer_id}", response_model=list[EquipmentDocument])
def list_equipment_by_transformer(transformer_id: str, limit: LimitQuery = 50):
    return service.list_equipment_by_transformer(
        transformer_id=transformer_id,
        limit=limit,
    )


@router.post("", response_model=EquipmentDocument, status_code=status.HTTP_201_CREATED)
def create_equipment(equipment: dict):
    try:
        return service.create_equipment(equipment=equipment)
    except service.EquipmentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except repository.DuplicateEquipmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch("/{equipment_id}", response_model=EquipmentDocument)
def update_equipment(equipment_id: str, updates: dict):
    try:
        equipment = service.update_equipment(
            equipment_id=equipment_id,
            updates=updates,
        )
    except service.EquipmentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found.",
        )
    return equipment


@router.get("/{equipment_id}", response_model=EquipmentDocument)
def get_equipment(equipment_id: str):
    equipment = service.get_equipment(equipment_id=equipment_id)
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found.",
        )
    return equipment
