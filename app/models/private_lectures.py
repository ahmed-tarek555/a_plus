from sqlalchemy import Column, Integer, ForeignKey, String, Numeric, Boolean, DateTime
from app.database import Base

class PrivateLecture(Base):
    __tablename__ = "private_lectures"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    link = Column(String, nullable=True)