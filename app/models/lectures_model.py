from sqlalchemy import Column, Integer, ForeignKey, String
from app.database import Base

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(50), nullable=False)
    price = Column(Integer, nullable=False)
    video_id = Column(String, nullable=False)
    material_public_id = Column(String, nullable=True)