from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, String
from app.database import Base

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "type", name="unique_user_persmission"),
    )