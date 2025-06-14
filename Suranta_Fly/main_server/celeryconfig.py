from celery.schedules import crontab
from .core.config import settings
from celery.signals import task_failure, worker_ready
import logging

logger = logging.getLogger(__name__)

# Broker and backend settings
broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL

# Task serialization settings
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Worker settings for optimal performance
worker_prefetch_multiplier = 1  # Process one task at a time
worker_max_tasks_per_child = 1000  # Restart worker after 1000 tasks
worker_max_memory_per_child = 200000  # 200MB memory limit
worker_concurrency = 4  # Number of worker processes

# Task routing with priorities
task_routes = {
    'app.services.monitoring.*': {
        'queue': 'monitoring',
        'routing_key': 'monitoring.high',
        'time_limit': 300,
        'soft_time_limit': 240
    },
    'app.services.notifications.*': {
        'queue': 'notifications',
        'routing_key': 'notifications.low',
        'time_limit': 60,
        'soft_time_limit': 45
    }
}

# Task time limits and resource management
task_time_limit = 300  # 5 minutes
task_soft_time_limit = 240  # 4 minutes

# Error handling and task acknowledgment
task_acks_late = True  # Only acknowledge task after it's completed
task_reject_on_worker_lost = True  # Requeue task if worker dies
task_track_started = True  # Track when task starts

# Logging configuration
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Task priority settings
task_queue_max_priority = 10
task_default_priority = 5

# Result backend settings
result_expires = 3600  # Results expire after 1 hour
result_backend_transport_options = {
    'retry_policy': {
        'timeout': 5.0
    }
}

# Security settings
security_key = settings.SECRET_KEY
security_certificate = settings.SSL_CERT_PATH
security_cert_store = settings.SSL_CERT_STORE

# SSL configuration
broker_use_ssl = {
    'ssl_cert_reqs': 'required',
    'ssl_ca_certs': settings.SSL_CA_CERTS,
    'ssl_certfile': settings.SSL_CERT_FILE,
    'ssl_keyfile': settings.SSL_KEY_FILE,
}

# Redis SSL configuration
redis_use_ssl = True
redis_ssl_ca_certs = settings.REDIS_SSL_CA_CERTS

# Task execution settings
task_ignore_result = False  # Store task results
task_store_errors_even_if_ignored = True  # Store error results
task_compression = 'gzip'  # Compress task messages

# Worker process settings
worker_pool_restarts = True  # Enable pool restarts
worker_send_task_events = True  # Send task events
worker_enable_remote_control = True  # Enable remote control

# Task execution optimization
task_always_eager = False  # Don't execute tasks locally
task_eager_propagates = True  # Propagate exceptions in eager mode
task_publish_retry = True  # Retry publishing tasks
task_publish_retry_policy = {
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 0.5,
}

# Beat scheduler with monitoring
beat_schedule = {
    'monitor-active-flights': {
        'task': 'app.services.monitoring.monitor_active_flights',
        'schedule': crontab(minute='*/5'),
        'options': {
            'expires': 300,
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.5,
            }
        }
    }
}

# Beat scheduler optimization
beat_max_loop_interval = 60  # Maximum time between scheduler checks
beat_sync_every = 60  # Sync schedule every 60 seconds
beat_scheduler = 'celery.beat.PersistentScheduler'  # Use persistent scheduler

# Task monitoring
@task_failure.connect
def handle_task_failure(task_id, exception, args, kwargs, traceback, einfo, **kw):
    """
    Handle task failures and send alerts.
    """
    logger.error(f"Task {task_id} failed: {str(exception)}")
    # Send alert to monitoring system
    send_alert(f"Task {task_id} failed: {str(exception)}")

@worker_ready.connect
def handle_worker_ready(**_):
    """
    Handle worker startup and health checks.
    """
    logger.info("Worker is ready")
    # Perform health checks
    check_worker_health()

# Audit logging
task_send_sent_event = True 