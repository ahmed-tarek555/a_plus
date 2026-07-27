from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from app.database import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    is_choices = Column(Boolean, nullable=False)
    head = Column(String, nullable=False)
    correct_choice = Column(String, nullable=True)
    mark = Column(Integer, nullable=False)