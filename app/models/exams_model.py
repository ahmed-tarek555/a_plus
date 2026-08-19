from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.database import Base

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(50), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)