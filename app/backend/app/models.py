"""
SQLAlchemy Models for Job Application Tracker
=============================================
Purpose:
  Defines the database schema for job applications stored in the preview database.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


class Application(Base):
    """
    Represents a single job application record.
    """
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), nullable=False, index=True)
    role = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="applied", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, company='{self.company}', role='{self.role}', status='{self.status}')>"
