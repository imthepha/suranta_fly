from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    monitoring_tasks = relationship("MonitoringTask", back_populates="user")

class MonitoringTask(Base):
    __tablename__ = "monitoring_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    flight_number = Column(String, index=True)
    origin = Column(String)
    destination = Column(String)
    departure_date = Column(DateTime)
    return_date = Column(DateTime, nullable=True)
    max_price = Column(Float, nullable=True)
    status = Column(String)  # active, paused, completed
    interval_minutes = Column(Integer, default=5)
    last_check = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notification_settings = Column(JSON)
    auto_purchase = Column(Boolean, default=False)
    statistics = Column(JSON, nullable=True)  # Store task statistics

    user = relationship("User", back_populates="monitoring_tasks")
    availability_logs = relationship("AvailabilityLog", back_populates="task")

class AvailabilityLog(Base):
    __tablename__ = "availability_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("monitoring_tasks.id"))
    check_time = Column(DateTime, default=datetime.utcnow)
    is_available = Column(Boolean)
    price = Column(Float, nullable=True)
    seats_available = Column(Integer, nullable=True)
    raw_response = Column(JSON, nullable=True)

    task = relationship("MonitoringTask", back_populates="availability_logs")

class PurchaseAttempt(Base):
    __tablename__ = "purchase_attempts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("monitoring_tasks.id"))
    attempt_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # success, failed, pending
    error_message = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    raw_response = Column(JSON, nullable=True) 