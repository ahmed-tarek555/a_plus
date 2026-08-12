from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from app.database import Base

class LecturePurchase(Base):
    __tablename__ = "lec_purchases"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "lecture_id", name="unique_student_lecture"),
    )