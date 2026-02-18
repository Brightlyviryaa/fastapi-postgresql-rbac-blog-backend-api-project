from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.base import Base

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft, published
    visibility: Mapped[str] = mapped_column(String, default="public")  # public, private
    
    # SEO & Media
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    meta_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Analytics & Journal Info
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    reading_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # In minutes
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    volume: Mapped[Optional[str]] = mapped_column(String, nullable=True) # e.g., "Vol. 24"
    issue: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., "Jan 2026"

    # Foreign Keys
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)

    # Vector Search
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)

    # Timestamps & Soft Delete
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post")
    category = relationship("Category", back_populates="posts")
    tags = relationship("Tag", secondary="post_tags", back_populates="posts")
