import logging
import json
from datetime import datetime
from typing import Any, Dict
import structlog
from pythonjsonlogger import jsonlogger
from functools import lru_cache

@lru_cache()
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    Uses caching to ensure we don't create multiple loggers with the same name.
    """
    return logging.getLogger(name)

def setup_logging():
    """Configure centralized logging with JSON format"""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Add JSON formatter
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    ))
    root_logger.addHandler(json_handler)

    # Configure Celery logging
    celery_logger = logging.getLogger('celery')
    celery_logger.setLevel(logging.INFO)
    celery_logger.addHandler(json_handler)

    # Configure FastAPI logging
    fastapi_logger = logging.getLogger('fastapi')
    fastapi_logger.setLevel(logging.INFO)
    fastapi_logger.addHandler(json_handler)

class TaskLogger:
    """Custom logger for task-specific logging"""
    def __init__(self, task_id: int):
        self.task_id = task_id
        self.logger = structlog.get_logger()

    def log_task_event(self, event_type: str, **kwargs):
        """Log task event with consistent format"""
        self.logger.info(
            event_type,
            task_id=self.task_id,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        ) 