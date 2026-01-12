from pydantic import BaseModel

class MetaBySpecResponse(BaseModel):
    class_name: str
    spec: str
    meta: float | None
    spec_type: str
    encounter_id: int

    class Config:
        from_attributes = True

