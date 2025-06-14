from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .database import get_db, engine
from . import models, schemas, crud
from .core.config import settings
from .core.security import create_access_token, get_current_user
from .routers import auth, flights, monitoring, admin, monitoring_dashboard
from .core.logger import get_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Airline Ticket Monitoring System",
    description="API for monitoring and purchasing airline tickets",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(flights.router, prefix="/api/flights", tags=["Flights"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(monitoring_dashboard.router)

@app.get("/")
async def root():
    return {"message": "Airline Ticket Monitoring System API"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/dashboard")
async def dashboard(request: Request):
    """
    Serve the monitoring dashboard.
    """
    return templates.TemplateResponse(
        "monitoring_dashboard.html",
        {"request": request}
    )

@app.on_event("startup")
async def startup_event():
    """
    Initialize application on startup.
    """
    logger.info("Application starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on application shutdown.
    """
    logger.info("Application shutting down...") 