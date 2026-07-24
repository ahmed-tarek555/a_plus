from pydantic import BaseModel
from decimal import Decimal

class AddCourse(BaseModel):
    subject: str
    price: Decimal