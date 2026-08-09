from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime


class CreatePrivate(BaseModel):
    title: str
    subject: str
    start_date: datetime
    price: Decimal

class PrivateLink(BaseModel):
    link: str

class ManualBook(BaseModel):
    title: str
    subject: str
    start_date: datetime
    phone_number: str