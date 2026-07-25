from pydantic import BaseModel
from decimal import Decimal

class AddCourse(BaseModel):
    price: Decimal
    stage: str
    level: int
    subject: str