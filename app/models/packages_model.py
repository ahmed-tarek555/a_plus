from sqlalchemy import Column, Integer, Numeric, String
from app.database import Base

class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)