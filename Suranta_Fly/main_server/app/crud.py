from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import List, Optional, Dict, Any

from . import models, schemas
from .core.security import get_password_hash, verify_password

# User operations
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

# Monitoring task operations
def get_monitoring_task(db: Session, task_id: int) -> Optional[models.MonitoringTask]:
    return db.query(models.MonitoringTask).filter(models.MonitoringTask.id == task_id).first()

def get_user_monitoring_tasks(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100
) -> List[models.MonitoringTask]:
    return db.query(models.MonitoringTask)\
        .filter(models.MonitoringTask.user_id == user_id)\
        .offset(skip)\
        .limit(limit)\
        .all()

def create_monitoring_task(
    db: Session, 
    task: schemas.MonitoringTaskCreate, 
    user_id: int
) -> models.MonitoringTask:
    db_task = models.MonitoringTask(
        **task.dict(),
        user_id=user_id,
        status="active"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_monitoring_task(
    db: Session, 
    task_id: int, 
    task_update: schemas.MonitoringTaskUpdate
) -> Optional[models.MonitoringTask]:
    db_task = get_monitoring_task(db, task_id)
    if not db_task:
        return None
    
    update_data = task_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task

def get_active_monitoring_tasks(db: Session) -> List[models.MonitoringTask]:
    return db.query(models.MonitoringTask)\
        .filter(models.MonitoringTask.status == "active")\
        .all()

# Availability log operations
def create_availability_log(
    db: Session, 
    log: schemas.AvailabilityLogCreate
) -> models.AvailabilityLog:
    db_log = models.AvailabilityLog(**log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_task_availability_logs(
    db: Session, 
    task_id: int, 
    skip: int = 0, 
    limit: int = 100
) -> List[models.AvailabilityLog]:
    return db.query(models.AvailabilityLog)\
        .filter(models.AvailabilityLog.task_id == task_id)\
        .order_by(desc(models.AvailabilityLog.check_time))\
        .offset(skip)\
        .limit(limit)\
        .all()

# Purchase attempt operations
def create_purchase_attempt(
    db: Session, 
    attempt: schemas.PurchaseAttemptCreate
) -> models.PurchaseAttempt:
    db_attempt = models.PurchaseAttempt(**attempt.dict())
    db.add(db_attempt)
    db.commit()
    db.refresh(db_attempt)
    return db_attempt

def get_task_purchase_attempts(
    db: Session, 
    task_id: int, 
    skip: int = 0, 
    limit: int = 100
) -> List[models.PurchaseAttempt]:
    return db.query(models.PurchaseAttempt)\
        .filter(models.PurchaseAttempt.task_id == task_id)\
        .order_by(desc(models.PurchaseAttempt.attempt_time))\
        .offset(skip)\
        .limit(limit)\
        .all() 