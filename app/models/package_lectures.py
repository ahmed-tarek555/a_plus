from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class PackageLecture(Base):
    __tablename__ = "package_lectures"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False)