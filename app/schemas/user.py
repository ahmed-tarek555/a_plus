from pydantic import BaseModel

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    password: str
    parent_name: str = None
    parent_phone_number: str = None
    role: str
    level: int = None
    subject: str = None

class UserLogin(BaseModel):
    email: str
    password: str