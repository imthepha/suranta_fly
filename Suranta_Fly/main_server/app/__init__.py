from redis import Redis
from .core.config import settings
from .services.monitoring import TaskLockManager
from .core.logger import setup_logging

# Initialize logging
setup_logging()

# Initialize Redis client
redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    ssl=settings.REDIS_USE_SSL,
    ssl_ca_certs=settings.REDIS_SSL_CA_CERTS
)

# Initialize TaskLockManager as a singleton
lock_manager = TaskLockManager(redis_client)

__all__ = ['lock_manager'] 