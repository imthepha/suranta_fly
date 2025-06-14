# Airline Ticket Monitoring System

A production-grade system for monitoring airline ticket availability and automated purchasing.

## Features

- Real-time monitoring of airline ticket availability
- Automated purchase triggers when tickets become available
- Web-based admin interface for configuration
- Secure authentication system
- Comprehensive logging and monitoring
- Scalable architecture using Celery for background tasks
- Docker support for easy deployment

## System Requirements

- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- Node.js 16+ (for frontend)

## Installation

1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables (copy .env.example to .env and configure)
5. Initialize the database:
   ```bash
   alembic upgrade head
   ```
6. Start the backend services:
   ```bash
   # Start Redis
   redis-server

   # Start Celery worker
   celery -A app.worker worker --loglevel=info

   # Start the API server
   uvicorn app.main:app --reload
   ```

## Configuration

The system uses environment variables for configuration. Create a `.env` file with the following variables:

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Development

- Backend API: FastAPI
- Frontend: React
- Database: PostgreSQL
- Task Queue: Celery with Redis
- Authentication: JWT tokens

## Production Deployment

The system is designed to be deployed using Docker Compose. See the `docker-compose.yml` file for configuration details.

## License

Proprietary - All rights reserved 