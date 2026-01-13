from pydantic import BaseModel
from typing import Optional

class MetaBySpecResponse(BaseModel):
    class_name: str
    spec: str
    meta: int | None
    spec_type: str
    encounter_id: Optional[int] = None

    class Config:
        from_attributes = True

