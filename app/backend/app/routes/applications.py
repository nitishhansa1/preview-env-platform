"""
Application Tracker API Routes
==============================
Purpose:
  Provides full CRUD operations for managing job applications.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Application
from app.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/applications", tags=["Applications"])


@router.get("", response_model=List[ApplicationResponse])
def list_applications(
    status: Optional[ApplicationStatus] = Query(None, description="Filter by application status"),
    db: Session = Depends(get_db),
):
    """
    Retrieve all job applications, optionally filtered by status.
    """
    query = db.query(Application)
    if status:
        query = query.filter(Application.status == status.value)
    applications = query.order_by(Application.created_at.desc()).all()
    return applications


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    application_in: ApplicationCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new job application.
    """
    application = Application(
        company=application_in.company,
        role=application_in.role,
        status=application_in.status.value,
        notes=application_in.notes,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    logger.info(f"Created application {application.id} for company '{application.company}'")
    return application


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a single job application by ID.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found",
        )
    return application


@router.put("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    application_in: ApplicationUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing job application by ID.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found",
        )

    update_data = application_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            setattr(application, field, value.value if hasattr(value, "value") else str(value))
        else:
            setattr(application, field, value)

    db.commit()
    db.refresh(application)
    logger.info(f"Updated application {application.id}")
    return application


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a job application by ID.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found",
        )

    db.delete(application)
    db.commit()
    logger.info(f"Deleted application {application_id}")
    return None
