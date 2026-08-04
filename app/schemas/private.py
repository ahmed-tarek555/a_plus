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

# example payload:
#
# {
#     "title": "private lecture",
#     "subject": "math",
#     "start_date": "some date",
#     "price": 200
# }