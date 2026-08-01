from pydantic import BaseModel
from typing import List
from decimal import Decimal


class PackageItem(BaseModel):
    course_id: int

class PackageCreate(BaseModel):
    title: str
    price: Decimal
    courses_ids: List[PackageItem]


# example payload:
#
# {
#     "title": some title,
#     "price": some price,
#     "courses_ids": [
#     id1, id2, .....
# ]
# }