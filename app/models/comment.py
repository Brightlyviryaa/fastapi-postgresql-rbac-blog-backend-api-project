from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Foreign Keys
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
