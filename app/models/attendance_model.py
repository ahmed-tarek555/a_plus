from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from app.database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("lecture_id", "student_id", name="unique_student_attendance"),
    )