from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class PackageItem(Base):
    __tablename__ = "package_items"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False)