from equipment import repository


class EquipmentValidationError(ValueError):
    pass


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def list_equipment(
    limit: int,
    equipment_type: str | None = None,
    manufacturer: str | None = None,
) -> list[dict]:
    return repository.list_equipment(
        limit=limit,
        equipment_type=_normalize_filter(equipment_type),
        manufacturer=_normalize_filter(manufacturer),
    )


def get_equipment(equipment_id: str) -> dict | None:
    return repository.get_equipment(equipment_id=equipment_id.strip())


def create_equipment(equipment: dict) -> dict:
    normalized = dict(equipment)
    normalized.pop("_id", None)

    equipment_id = normalized.get("equipment_id")
    if not isinstance(equipment_id, str) or not equipment_id.strip():
        raise EquipmentValidationError("equipment_id is required.")

    normalized["equipment_id"] = equipment_id.strip()
    return repository.create_equipment(equipment=normalized)


def update_equipment(equipment_id: str, updates: dict) -> dict | None:
    normalized = dict(updates)
    normalized.pop("_id", None)
    normalized.pop("equipment_id", None)

    if not normalized:
        raise EquipmentValidationError("At least one update field is required.")

    return repository.update_equipment(
        equipment_id=equipment_id.strip(),
        updates=normalized,
    )


def list_equipment_by_type(equipment_type: str, limit: int) -> list[dict]:
    return repository.list_equipment_by_type(
        equipment_type=equipment_type.strip(),
        limit=limit,
    )


def list_equipment_by_transformer(transformer_id: str, limit: int) -> list[dict]:
    return repository.list_equipment_by_transformer(
        transformer_id=transformer_id.strip(),
        limit=limit,
    )
