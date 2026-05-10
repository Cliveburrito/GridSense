from pydantic import BaseModel, ConfigDict


class EquipmentDocument(BaseModel):
    id: str | None = None
    equipment_id: str
    type: str
    manufacturer: str | None = None

    model_config = ConfigDict(extra="allow")
