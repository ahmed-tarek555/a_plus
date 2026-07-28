from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.database import Base

class SubmittedHomework(Base):
    __tablename__ = "submitted_homeworks"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    public_id = Column(String, nullable=False)