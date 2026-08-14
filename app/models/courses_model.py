from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Boolean
from app.database import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    stage = Column(String, nullable=False)
    level = Column(Integer, nullable=False)
    subject = Column(String, nullable=False)
    cover_public_id = Column(String, nullable=False)
    is_public = Column(Boolean, nullable=False)