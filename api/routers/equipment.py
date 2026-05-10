from datetime import date, datetime
from typing import Annotated, Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from db.mongo import get_mongo_database
from models.mongo import EquipmentDocument

router = APIRouter(prefix="/equipment", tags=["equipment"])

LimitQuery = Annotated[int, Query(ge=1, le=200)]


class EquipmentValidationError(ValueError):
    pass


class DuplicateEquipmentError(Exception):
    pass


def _equipment_collection():
    return get_mongo_database().equipment


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _serialize_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _serialize_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None

    serialized = {key: _serialize_value(value) for key, value in document.items()}
    object_id = serialized.pop("_id", None)
    if object_id is not None:
        serialized["id"] = object_id
    return serialized


async def _list_equipment_documents(
    limit: int,
    equipment_type: str | None = None,
    manufacturer: str | None = None,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if equipment_type:
        query["type"] = equipment_type
    if manufacturer:
        query["manufacturer"] = manufacturer

    cursor = _equipment_collection().find(query).sort("equipment_id", 1).limit(limit)
    return [_serialize_document(document) async for document in cursor]


async def _get_equipment_document(equipment_id: str) -> dict[str, Any] | None:
    document = await _equipment_collection().find_one({"equipment_id": equipment_id})
    return _serialize_document(document)


@router.get("", response_model=list[EquipmentDocument])
async def list_equipment(
    limit: LimitQuery = 50,
    equipment_type: Annotated[str | None, Query(alias="type")] = None,
    manufacturer: str | None = None,
):
    return await _list_equipment_documents(
        limit=limit,
        equipment_type=_normalize_filter(equipment_type),
        manufacturer=_normalize_filter(manufacturer),
    )


@router.get("/type/{equipment_type}", response_model=list[EquipmentDocument])
async def list_equipment_by_type(equipment_type: str, limit: LimitQuery = 50):
    return await _list_equipment_documents(
        limit=limit,
        equipment_type=equipment_type.strip(),
    )


@router.get("/transformer/{transformer_id}", response_model=list[EquipmentDocument])
async def list_equipment_by_transformer(transformer_id: str, limit: LimitQuery = 50):
    cursor = (
        _equipment_collection()
        .find(
            {
                "$or": [
                    {"equipment_id": transformer_id.strip()},
                    {"transformer_id": transformer_id.strip()},
                ]
            }
        )
        .sort("equipment_id", 1)
        .limit(limit)
    )
    return [_serialize_document(document) async for document in cursor]


@router.post("", response_model=EquipmentDocument, status_code=status.HTTP_201_CREATED)
async def create_equipment(equipment: dict):
    normalized = dict(equipment)
    normalized.pop("_id", None)

    equipment_id = normalized.get("equipment_id")
    if not isinstance(equipment_id, str) or not equipment_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="equipment_id is required.",
        )

    normalized["equipment_id"] = equipment_id.strip()
    try:
        await _equipment_collection().insert_one(normalized)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Equipment with this equipment_id already exists.",
        ) from exc

    return await _get_equipment_document(normalized["equipment_id"])


@router.patch("/{equipment_id}", response_model=EquipmentDocument)
async def update_equipment(equipment_id: str, updates: dict):
    normalized = dict(updates)
    normalized.pop("_id", None)
    normalized.pop("equipment_id", None)

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one update field is required.",
        )

    equipment = await _equipment_collection().find_one_and_update(
        {"equipment_id": equipment_id.strip()},
        {"$set": normalized},
        return_document=ReturnDocument.AFTER,
    )

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found.",
        )
    return _serialize_document(equipment)


@router.get("/{equipment_id}", response_model=EquipmentDocument)
async def get_equipment(equipment_id: str):
    equipment = await _get_equipment_document(equipment_id.strip())
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found.",
        )
    return equipment
