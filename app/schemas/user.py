from pydantic import BaseModel

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    username: str
    phone_number: str
    password: str
    parent_name: str = None
    parent_phone_number: str = None
    role: str
    level: int = None
    stage: str = None

class UserLogin(BaseModel):
    username: str
    password: str

class EditProfile(BaseModel):
    first_name: str = None
    last_name: str = None
    phone_number: str = None
    password: str = None