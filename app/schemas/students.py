from pydantic import BaseModel

class SearchStudents(BaseModel):
    stage: str = None
    level: int = None

class EditLevel(BaseModel):
    old_stage: str
    old_level: int
    new_stage: str
    new_level: int