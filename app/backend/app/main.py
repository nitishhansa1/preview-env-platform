"""
Preview Environment Platform - FastAPI Application Entrypoint
=============================================================
Purpose:
  Entrypoint for the Job Application Tracker REST API.
  Handles application lifecycle (DB connection retry, schema migration, seed data),
  structured JSON logging, CORS headers, Kubernetes health/readiness probes, and
  metadata version endpoints.
"""

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import setup_logging
from app.database import engine, SessionLocal, Base, check_db_connection
from app.models import Application
from app.schemas import VersionResponse, HealthResponse, ReadinessResponse
from app.routes.applications import router as applications_router

# Initialize structured JSON logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("preview-backend")


def seed_sample_data(db: Session):
    """
    Seeds initial sample applications if the table is empty.
    Ensures every newly created ephemeral PR preview environment has rich,
    interactive data immediately upon deployment.
    """
    count = db.query(Application).count()
    if count == 0:
        logger.info("Applications table is empty. Seeding 3 initial sample records...")
        sample_apps = [
            Application(
                company="Google",
                role="Senior Cloud Infrastructure Engineer",
                status="offer",
                notes="Completed 5 interview rounds. Offer received with team match in Cloud Platforms.",
            ),
            Application(
                company="Stripe",
                role="Platform DevOps Engineer",
                status="interview",
                notes="Technical system design interview scheduled for next Tuesday.",
            ),
            Application(
                company="Shopify",
                role="Site Reliability Engineer",
                status="applied",
                notes="Applied via referral link; waiting for recruiter screening.",
            ),
        ]
        db.add_all(sample_apps)
        db.commit()
        logger.info("Successfully seeded sample job applications.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Context Manager.
    Runs startup tasks before accepting traffic:
      1. Retries connecting to the PostgreSQL database (retrying up to 5 times
         with backoff to allow Postgres to initialize in Kubernetes/Docker).
      2. Automatically generates database tables.
      3. Seeds initial preview data if empty.
    """
    logger.info(
        "Starting application",
        extra={"extra": {"version": settings.APP_VERSION, "pr": settings.PR_NUMBER, "sha": settings.GIT_SHA}},
    )

    # 1. Database connection retry loop
    max_retries = 5
    retry_interval = 2
    connected = False

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Checking database connection (attempt {attempt}/{max_retries})...")
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            connected = True
            logger.info("Database connection established successfully.")
            break
        except Exception as exc:
            logger.warning(
                f"Database connection attempt {attempt} failed: {exc}. Retrying in {retry_interval}s..."
            )
            time.sleep(retry_interval)

    # 2. Create tables and seed data if connected
    if connected:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_sample_data(db)
        finally:
            db.close()
    else:
        logger.error("Could not establish database connection after multiple attempts.")

    yield

    logger.info("Shutting down application...")


# FastAPI Application instance
app = FastAPI(
    title="Job Application Tracker API",
    description="Backend service for ephemeral PR preview environments on Kubernetes.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register business logic routes
app.include_router(applications_router)


# ==============================================================================
# Kubernetes Health & Readiness Probes
# ==============================================================================

@app.get("/healthz", response_model=HealthResponse, tags=["Observability"])
@app.get("/api/health", response_model=HealthResponse, tags=["Observability"])
def healthz():
    """
    Liveness Probe (/healthz):
    --------------------------
    Why this endpoint exists:
      Kubernetes kubelet calls this probe to detect if the container process is alive.
      If this endpoint returns a failure status (non-200) or fails to respond,
      Kubernetes will automatically restart the pod container.

      *CRITICAL RULE*: Liveness probes MUST NOT check external dependencies like
      databases or third-party APIs. If PostgreSQL is temporarily restarting,
      failing liveness would cause Kubernetes to enter a cascading restart loop
      across all backend pods.
    """
    return {"status": "alive"}


@app.get("/readyz", response_model=ReadinessResponse, tags=["Observability"])
def readyz(response: Response):
    """
    Readiness Probe (/readyz):
    ---------------------------
    Why this endpoint exists:
      Kubernetes calls this probe to determine whether the pod is ready to accept
      incoming user network traffic through the Ingress and Service.

      Unlike liveness, readiness DOES check internal readiness (e.g. database connectivity).
      If the database is still initializing or temporarily unavailable, this probe
      returns HTTP 503 (Service Unavailable). Kubernetes will temporarily remove
      this pod's IP from the Service endpoints so users do not experience HTTP 500 errors.
      Once the DB comes online, traffic resumes automatically without restarting the pod.
    """
    is_db_ready = check_db_connection()
    if not is_db_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "disconnected"}
    return {"status": "ready", "database": "connected"}


@app.get("/api/version", response_model=VersionResponse, tags=["Metadata"])
def get_version():
    """
    Preview Environment Version Metadata (/api/version):
    -----------------------------------------------------
    Why this endpoint exists:
      Returns the runtime version, Git commit SHA, and Pull Request number injected
      into the container via environment variables. This allows the preview dashboard
      and QA engineers to instantly verify which Git commit is currently running.
    """
    return {
        "app_version": settings.APP_VERSION,
        "git_sha": settings.GIT_SHA,
        "pr_number": settings.PR_NUMBER,
    }


@app.get("/", tags=["Metadata"])
def root():
    """Root redirect / information endpoint."""
    return {
        "service": "Job Application Tracker API",
        "docs": "/docs",
        "pr": settings.PR_NUMBER,
        "version": settings.APP_VERSION,
    }
