from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from app.database import Base

class SubmittedExam(Base):
    __tablename__ = "submitted_exams"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    mark = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "exam_id", name="unique_submitted_exam"),
    )