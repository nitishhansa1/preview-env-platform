"""
Pydantic Schemas for Job Application Tracker
============================================
Purpose:
  Defines request and response validation models and serialization contracts.
"""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"


class ApplicationBase(BaseModel):
    company: str = Field(..., min_length=1, max_length=255, description="Company name")
    role: str = Field(..., min_length=1, max_length=255, description="Job title / position")
    status: ApplicationStatus = Field(default=ApplicationStatus.APPLIED, description="Current application status")
    notes: Optional[str] = Field(default=None, description="Additional notes or interview details")


class ApplicationCreate(ApplicationBase):
    """Schema for creating a new job application."""
    pass


class ApplicationUpdate(BaseModel):
    """Schema for updating an existing job application (all fields optional)."""
    company: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role: Optional[str] = Field(default=None, min_length=1, max_length=255)
    status: Optional[ApplicationStatus] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class ApplicationResponse(ApplicationBase):
    """Schema for returning job application details."""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VersionResponse(BaseModel):
    """Schema for the preview environment version endpoint."""
    app_version: str
    git_sha: str
    pr_number: str


class HealthResponse(BaseModel):
    """Schema for liveness probe response."""
    status: str


class ReadinessResponse(BaseModel):
    """Schema for readiness probe response."""
    status: str
    database: str
