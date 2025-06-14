from celery import Celery
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
import json
from typing import Dict, Any, Optional, Set
from contextlib import contextmanager
from redis.lock import Lock
from redis.exceptions import LockError, RedisError
import statistics
from celery.schedules import crontab
from tenacity import retry, stop_after_attempt, wait_exponential
import time
import signal
import atexit
import os

from ..database import SessionLocal
from ..core.config import settings
from .. import crud, schemas, models
from .notifications import send_notification
from .scrapers.alibaba import AlibabaScraper
from ..core.logger import get_logger
from .. import lock_manager

# Configure logging
logger = get_logger(__name__)

# Configure Celery
celery = Celery(
    'monitoring',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery Beat schedule
celery.conf.beat_schedule = {
    'monitor-active-flights': {
        'task': 'app.services.monitoring.monitor_active_flights',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
    },
}

# Initialize scraper
scraper = AlibabaScraper()

class TaskLockManager:
    """
    Manages Redis-based task locks for preventing concurrent task execution.
    
    This class provides a centralized way to manage task locks using Redis,
    ensuring that only one instance of a task can run at a time. It includes
    features for lock acquisition, release, and cleanup.
    
    Features:
    - Lock acquisition with timeout
    - Automatic lock release
    - Lock cleanup
    - Error handling
    - Detailed logging
    """
    
    def __init__(self, redis_client):
        """
        Initialize the TaskLockManager.
        
        Args:
            redis_client: Redis client instance from Celery backend
        """
        self.redis_client = redis_client
        self.active_locks: Dict[int, dict] = {}
        self.lock_ttl = 3600  # 1 hour TTL
        self.cleanup_interval = 300  # 5 minutes
        self._register_cleanup_handlers()
    
    def _register_cleanup_handlers(self):
        """Register signal handlers and cleanup on exit"""
        # Handle SIGTERM
        signal.signal(signal.SIGTERM, self._handle_termination)
        # Handle SIGINT
        signal.signal(signal.SIGINT, self._handle_termination)
        # Register cleanup on normal exit
        atexit.register(self.cleanup_all_locks)

    def _handle_termination(self, signum, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {signum}, cleaning up locks...")
        self.cleanup_all_locks()
        raise SystemExit(0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def acquire_lock(self, task_id: int, timeout: int = 300) -> Optional[Lock]:
        """
        Acquire a Redis lock with improved race condition handling.
        """
        lock_key = f"task_lock:{task_id}"
        try:
            # Check for existing lock with TTL
            current_ttl = self.redis_client.ttl(lock_key)
            if current_ttl > 0:
                logger.warning(f"Lock exists for task {task_id} with TTL {current_ttl}s")
                return None

            # Use blocking with timeout for fair lock acquisition
            lock = self.redis_client.lock(
                lock_key,
                timeout=timeout,
                blocking=True,
                blocking_timeout=5  # Wait up to 5 seconds for lock
            )
            
            if lock.acquire():
                # Set TTL and store lock info
                self.redis_client.expire(lock_key, self.lock_ttl)
                self.active_locks[task_id] = {
                    'lock': lock,
                    'acquired_at': time.time(),
                    'task_id': task_id,
                    'worker_id': os.getpid()
                }
                logger.info(f"Lock acquired for task {task_id} by worker {os.getpid()}")
                return lock
                
            logger.warning(f"Could not acquire lock for task {task_id} after timeout")
            return None
            
        except (LockError, RedisError) as e:
            logger.error(f"Redis lock error: {str(e)}")
            return None
    
    def cleanup_all_locks(self):
        """Clean up all locks owned by this worker"""
        current_pid = os.getpid()
        locks_to_clean = [
            task_id for task_id, lock_info in self.active_locks.items()
            if lock_info['worker_id'] == current_pid
        ]
        
        for task_id in locks_to_clean:
            self.release_lock(task_id)
            logger.info(f"Cleaned up lock for task {task_id} during shutdown")

    def cleanup_stale_locks(self):
        """Clean up stale locks with improved detection"""
        current_time = time.time()
        stale_tasks = []
        
        for task_id, lock_info in self.active_locks.items():
            # Check if lock is stale
            if current_time - lock_info['acquired_at'] > self.lock_ttl:
                stale_tasks.append(task_id)
                continue
                
            # Verify lock still exists in Redis
            lock_key = f"task_lock:{task_id}"
            if not self.redis_client.exists(lock_key):
                stale_tasks.append(task_id)
                continue
                
            # Check if worker is still alive
            if not self._is_worker_alive(lock_info['worker_id']):
                stale_tasks.append(task_id)
        
        for task_id in stale_tasks:
            self.release_lock(task_id)
            logger.warning(f"Cleaned up stale lock for task {task_id}")

    def _is_worker_alive(self, worker_pid: int) -> bool:
        """Check if a worker process is still alive"""
        try:
            os.kill(worker_pid, 0)
            return True
        except OSError:
            return False

    def release_lock(self, task_id: int) -> bool:
        """
        Release a task lock.
        
        Args:
            task_id: The ID of the task whose lock should be released
        
        Returns:
            bool: True if lock was released successfully, False otherwise
        """
        if task_id not in self.active_locks:
            logger.warning(f"No active lock found for task {task_id}")
            return False
            
        try:
            lock = self.active_locks[task_id]['lock']
            lock.release()
            del self.active_locks[task_id]
            logger.info(f"Lock released for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error releasing lock for task {task_id}: {str(e)}")
            return False

@contextmanager
def get_db():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@celery.task(
    name="monitor_flight",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=240
)
def monitor_flight(self, task_id: int):
    """
    Celery task with proper lock handling and time limits.
    """
    task_logger = TaskLogger(task_id)
    task_logger.log_task_event("task_started")
    
    lock = lock_manager.acquire_lock(task_id, timeout=300)
    if not lock:
        task_logger.log_task_event("task_skipped", reason="lock_exists")
        return

    try:
        with get_db() as db:
            # Get task details
            task = crud.get_monitoring_task(db, task_id)
            if not task or task.status != "active":
                return

            # Check flight availability
            availability_data = scraper.check_availability(
                flight_number=task.flight_number,
                origin=task.origin,
                destination=task.destination,
                departure_date=task.departure_date,
                return_date=task.return_date
            )

            # Create availability log
            log = schemas.AvailabilityLogCreate(
                task_id=task_id,
                is_available=availability_data.get("is_available", False),
                price=availability_data.get("price"),
                seats_available=availability_data.get("seats_available"),
                raw_response=availability_data
            )
            crud.create_availability_log(db, log)

            # Update task last check time and statistics
            task.last_check = datetime.utcnow()
            update_task_statistics(db, task, availability_data)
            db.commit()
            db.refresh(task)

            # Handle availability
            if availability_data.get("is_available", False):
                handle_availability(db, task, availability_data)

    except Exception as e:
        task_logger.log_task_event("task_failed", error=str(e))
        self.retry(exc=e)
    finally:
        lock_manager.release_lock(task_id)
        task_logger.log_task_event("task_completed")

@celery.task(name="attempt_purchase")
def attempt_purchase(task_id: int, availability_data: Dict[str, Any]):
    """
    Attempt to purchase the flight.
    
    This task is protected by a Redis lock to prevent concurrent execution.
    The lock is automatically released when the task completes or fails.
    """
    # Acquire lock with 10-minute timeout
    lock = lock_manager.acquire_lock(task_id, timeout=600)
    if not lock:
        logger.warning(f"Purchase attempt for task {task_id} is already in progress")
        return

    try:
        with get_db() as db:
            task = crud.get_monitoring_task(db, task_id)
            if not task or task.status != "active":
                return

            # Create purchase attempt
            attempt = schemas.PurchaseAttemptCreate(
                task_id=task_id,
                status="pending",
                raw_response=availability_data
            )
            db_attempt = crud.create_purchase_attempt(db, attempt)

            # Attempt purchase
            try:
                purchase_result = scraper.attempt_purchase(
                    flight_number=task.flight_number,
                    origin=task.origin,
                    destination=task.destination,
                    departure_date=task.departure_date,
                    return_date=task.return_date,
                    price=availability_data.get("price")
                )

                # Update attempt status
                db_attempt.status = "success" if purchase_result.get("success", False) else "failed"
                db_attempt.transaction_id = purchase_result.get("transaction_id")
                db_attempt.error_message = purchase_result.get("error_message")
                db_attempt.raw_response = purchase_result
                db.commit()
                db.refresh(db_attempt)

                # Send notification
                notification_data = {
                    "type": "purchase_result",
                    "task_id": task.id,
                    "success": purchase_result.get("success", False),
                    "transaction_id": purchase_result.get("transaction_id"),
                    "error_message": purchase_result.get("error_message")
                }
                send_notification(task.user_id, notification_data)

            except Exception as e:
                logger.error(f"Error during purchase attempt for task {task_id}: {str(e)}")
                db_attempt.status = "failed"
                db_attempt.error_message = str(e)
                db.commit()
                db.refresh(db_attempt)

    except Exception as e:
        logger.error(f"Error in purchase task {task_id}: {str(e)}")
    finally:
        # Always release the lock
        lock_manager.release_lock(task_id)

@celery.task(name="monitor_active_flights")
def monitor_active_flights():
    """Monitor all active flights."""
    with get_db() as db:
        active_tasks = crud.get_active_monitoring_tasks(db)
        for task in active_tasks:
            monitor_flight.delay(task.id)

@celery.task(name="cleanup_old_logs")
def cleanup_old_logs():
    """Clean up old availability logs and purchase attempts."""
    with get_db() as db:
        # Delete logs older than 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        db.query(models.AvailabilityLog).filter(
            models.AvailabilityLog.check_time < thirty_days_ago
        ).delete()
        
        # Delete failed purchase attempts older than 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        db.query(models.PurchaseAttempt).filter(
            models.PurchaseAttempt.status == "failed",
            models.PurchaseAttempt.attempt_time < seven_days_ago
        ).delete()
        
        db.commit()

def update_task_statistics(db: Session, task: models.MonitoringTask, availability_data: Dict[str, Any]):
    """Update task statistics with the latest check results."""
    # Get recent logs for statistics
    recent_logs = crud.get_task_availability_logs(db, task.id, limit=100)
    
    if recent_logs:
        # Calculate price statistics
        prices = [log.price for log in recent_logs if log.price is not None]
        if prices:
            task.statistics = {
                "min_price": min(prices),
                "max_price": max(prices),
                "avg_price": statistics.mean(prices),
                "total_checks": len(recent_logs),
                "availability_rate": sum(1 for log in recent_logs if log.is_available) / len(recent_logs),
                "last_available": any(log.is_available for log in recent_logs[:5]),  # Check last 5 logs
                "last_price": prices[0] if prices else None,
                "last_check": datetime.utcnow().isoformat()
            }

def handle_availability(
    db: Session,
    task: models.MonitoringTask,
    availability_data: Dict[str, Any]
):
    """Handle flight availability based on task settings."""
    # Check price limit
    if task.max_price and availability_data.get("price", float("inf")) > task.max_price:
        return

    # Send notification
    notification_data = {
        "type": "flight_available",
        "task_id": task.id,
        "flight_number": task.flight_number,
        "origin": task.origin,
        "destination": task.destination,
        "departure_date": task.departure_date.isoformat(),
        "price": availability_data.get("price"),
        "seats_available": availability_data.get("seats_available")
    }
    send_notification(task.user_id, notification_data)

    # Handle auto-purchase
    if task.auto_purchase:
        attempt_purchase.delay(task.id, availability_data)

def start_monitoring_task(task_id: int):
    """Start monitoring a flight task."""
    # The task will be picked up by the periodic monitor_active_flights task
    return task_id

def stop_monitoring_task(task_id: int):
    """Stop monitoring a flight task."""
    # Revoke any pending tasks
    celery.control.revoke(task_id, terminate=True) 