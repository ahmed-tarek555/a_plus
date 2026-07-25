from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    level = Column(Integer, nullable=False)
    stage = Column(String, nullable=False)