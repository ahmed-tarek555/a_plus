from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    phone_number = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    parent_name = Column(String, nullable=True)
    parent_phone_number = Column(String, nullable=True)
    pfp_public_id = Column(String, nullable=True)
    role = Column(String, nullable=False)
    date_joined = Column(DateTime, nullable=False)
    is_active = Column(Boolean, nullable=False)