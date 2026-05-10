from datetime import date, datetime
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from db.mongo import get_mongo_database


class EquipmentRepositoryError(Exception):
    pass


class DuplicateEquipmentError(EquipmentRepositoryError):
    pass


def _equipment_collection():
    return get_mongo_database().equipment


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


def list_equipment(
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
    return [_serialize_document(document) for document in cursor]


def get_equipment(equipment_id: str) -> dict[str, Any] | None:
    document = _equipment_collection().find_one({"equipment_id": equipment_id})
    return _serialize_document(document)


def create_equipment(equipment: dict[str, Any]) -> dict[str, Any]:
    try:
        _equipment_collection().insert_one(equipment)
    except DuplicateKeyError as exc:
        raise DuplicateEquipmentError(
            "Equipment with this equipment_id already exists."
        ) from exc

    return get_equipment(equipment["equipment_id"])


def update_equipment(equipment_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    result = _equipment_collection().find_one_and_update(
        {"equipment_id": equipment_id},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    return _serialize_document(result)


def list_equipment_by_type(equipment_type: str, limit: int) -> list[dict[str, Any]]:
    cursor = (
        _equipment_collection()
        .find({"type": equipment_type})
        .sort("equipment_id", 1)
        .limit(limit)
    )
    return [_serialize_document(document) for document in cursor]


def list_equipment_by_transformer(
    transformer_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    cursor = (
        _equipment_collection()
        .find(
            {
                "$or": [
                    {"equipment_id": transformer_id},
                    {"transformer_id": transformer_id},
                ]
            }
        )
        .sort("equipment_id", 1)
        .limit(limit)
    )
    return [_serialize_document(document) for document in cursor]
