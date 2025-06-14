from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..core.security import get_current_active_user
from .. import crud, schemas, models
from ..services.monitoring import start_monitoring_task, stop_monitoring_task

router = APIRouter()

@router.post("/tasks/", response_model=schemas.MonitoringTask)
def create_task(
    task: schemas.MonitoringTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Validate dates
    if task.departure_date < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Departure date must be in the future"
        )
    
    if task.return_date and task.return_date <= task.departure_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return date must be after departure date"
        )
    
    # Create task
    db_task = crud.create_monitoring_task(db=db, task=task, user_id=current_user.id)
    
    # Start monitoring
    start_monitoring_task(db_task.id)
    
    return db_task

@router.get("/tasks/", response_model=List[schemas.MonitoringTask])
def read_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    tasks = crud.get_user_monitoring_tasks(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return tasks

@router.get("/tasks/{task_id}", response_model=schemas.MonitoringTask)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_task = crud.get_monitoring_task(db=db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_task

@router.put("/tasks/{task_id}", response_model=schemas.MonitoringTask)
def update_task(
    task_id: int,
    task_update: schemas.MonitoringTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_task = crud.get_monitoring_task(db=db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Handle status changes
    if task_update.status and task_update.status != db_task.status:
        if task_update.status == "active":
            start_monitoring_task(task_id)
        elif task_update.status == "paused":
            stop_monitoring_task(task_id)
    
    return crud.update_monitoring_task(db=db, task_id=task_id, task_update=task_update)

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_task = crud.get_monitoring_task(db=db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Stop monitoring if active
    if db_task.status == "active":
        stop_monitoring_task(task_id)
    
    # Update status to completed
    db_task.status = "completed"
    db.commit()
    
    return None

@router.get("/tasks/{task_id}/logs", response_model=List[schemas.AvailabilityLog])
def read_task_logs(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_task = crud.get_monitoring_task(db=db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    logs = crud.get_task_availability_logs(
        db=db, task_id=task_id, skip=skip, limit=limit
    )
    return logs

@router.get("/tasks/{task_id}/purchases", response_model=List[schemas.PurchaseAttempt])
def read_task_purchases(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_task = crud.get_monitoring_task(db=db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    purchases = crud.get_task_purchase_attempts(
        db=db, task_id=task_id, skip=skip, limit=limit
    )
    return purchases 