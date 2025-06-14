from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime, timedelta
import psutil
import socket
from .. import lock_manager
from ..core.logger import get_logger
from ..database import get_db_session
from sqlalchemy.orm import Session
from ..models import MonitoringTask, AvailabilityLog, PurchaseAttempt
from sqlalchemy import func
import json

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
logger = get_logger(__name__)

@router.get("/locks", response_model=List[Dict[str, Any]])
async def get_active_locks():
    """
    Get all currently active locks with their details.
    """
    active_locks = []
    for task_id, lock_info in lock_manager.active_locks.items():
        lock_key = f"task_lock:{task_id}"
        ttl = lock_manager.redis_client.ttl(lock_key)
        
        # Get process info if available
        process_info = {}
        if 'worker_id' in lock_info:
            try:
                process = psutil.Process(lock_info['worker_id'])
                process_info = {
                    'pid': process.pid,
                    'hostname': socket.gethostname(),
                    'cpu_percent': process.cpu_percent(),
                    'memory_percent': process.memory_percent(),
                    'create_time': datetime.fromtimestamp(process.create_time()).isoformat()
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_info = {'error': 'Process not accessible'}
        
        active_locks.append({
            'task_id': task_id,
            'lock_key': lock_key,
            'ttl_seconds': ttl,
            'acquired_at': lock_info['acquired_at'],
            'worker_info': process_info
        })
    
    return active_locks

@router.get("/stats", response_model=Dict[str, Any])
async def get_task_stats(db: Session = Depends(get_db_session)):
    """
    Get task statistics for the last 24 hours.
    """
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    
    # Get total tasks
    total_tasks = db.query(MonitoringTask).filter(
        MonitoringTask.created_at >= day_ago
    ).count()
    
    # Get success/fail counts from logs
    success_count = db.query(AvailabilityLog).filter(
        AvailabilityLog.created_at >= day_ago,
        AvailabilityLog.is_available == True
    ).count()
    
    fail_count = db.query(AvailabilityLog).filter(
        AvailabilityLog.created_at >= day_ago,
        AvailabilityLog.is_available == False
    ).count()
    
    # Get recent errors
    recent_errors = db.query(AvailabilityLog).filter(
        AvailabilityLog.created_at >= day_ago,
        AvailabilityLog.is_available == False
    ).order_by(AvailabilityLog.created_at.desc()).limit(10).all()
    
    error_logs = [{
        'task_id': log.task_id,
        'timestamp': log.created_at.isoformat(),
        'error': log.error_message
    } for log in recent_errors]
    
    # Calculate retry rate
    total_retries = db.query(func.count(AvailabilityLog.id)).filter(
        AvailabilityLog.created_at >= day_ago,
        AvailabilityLog.retry_count > 0
    ).scalar()
    
    retry_rate = (total_retries / total_tasks * 100) if total_tasks > 0 else 0
    
    return {
        'total_tasks_24h': total_tasks,
        'success_count': success_count,
        'fail_count': fail_count,
        'retry_rate_percent': retry_rate,
        'recent_errors': error_logs
    }

@router.post("/locks/{task_id}/release")
async def release_lock(task_id: int):
    """
    Forcefully release a lock for a specific task.
    Use with caution as this might interfere with running tasks.
    """
    try:
        if lock_manager.release_lock(task_id):
            logger.warning(f"Lock for task {task_id} was forcefully released")
            return {"message": f"Lock for task {task_id} released successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"No active lock found for task {task_id}")
    except Exception as e:
        logger.error(f"Error releasing lock for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}/history")
async def get_task_history(task_id: int, db: Session = Depends(get_db_session)):
    """
    Get detailed history for a specific task.
    """
    task = db.query(MonitoringTask).filter(MonitoringTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Get availability logs
    logs = db.query(AvailabilityLog).filter(
        AvailabilityLog.task_id == task_id
    ).order_by(AvailabilityLog.created_at.desc()).all()
    
    # Get purchase attempts
    attempts = db.query(PurchaseAttempt).filter(
        PurchaseAttempt.task_id == task_id
    ).order_by(PurchaseAttempt.created_at.desc()).all()
    
    return {
        'task_info': {
            'id': task.id,
            'status': task.status,
            'created_at': task.created_at.isoformat(),
            'last_checked': task.last_checked.isoformat() if task.last_checked else None,
            'statistics': task.statistics
        },
        'availability_logs': [{
            'timestamp': log.created_at.isoformat(),
            'is_available': log.is_available,
            'price': log.price,
            'error_message': log.error_message,
            'retry_count': log.retry_count
        } for log in logs],
        'purchase_attempts': [{
            'timestamp': attempt.created_at.isoformat(),
            'status': attempt.status,
            'error_message': attempt.error_message
        } for attempt in attempts]
    } 