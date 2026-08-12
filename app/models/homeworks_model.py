from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.database import Base

class Homework(Base):
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    public_id = Column(String, nullable=False)