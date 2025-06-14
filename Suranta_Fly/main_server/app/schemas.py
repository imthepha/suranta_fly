from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Monitoring task schemas
class MonitoringTaskBase(BaseModel):
    flight_number: str
    origin: str
    destination: str
    departure_date: datetime
    return_date: Optional[datetime] = None
    max_price: Optional[float] = None
    interval_minutes: int = 5
    auto_purchase: bool = False
    notification_settings: Dict[str, Any] = Field(default_factory=dict)

class MonitoringTaskCreate(MonitoringTaskBase):
    pass

class MonitoringTaskUpdate(BaseModel):
    status: Optional[str] = None
    interval_minutes: Optional[int] = None
    max_price: Optional[float] = None
    auto_purchase: Optional[bool] = None
    notification_settings: Optional[Dict[str, Any]] = None

class MonitoringTask(MonitoringTaskBase):
    id: int
    user_id: int
    status: str
    last_check: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Availability log schemas
class AvailabilityLogBase(BaseModel):
    is_available: bool
    price: Optional[float] = None
    seats_available: Optional[int] = None

class AvailabilityLogCreate(AvailabilityLogBase):
    task_id: int
    raw_response: Optional[Dict[str, Any]] = None

class AvailabilityLog(AvailabilityLogBase):
    id: int
    task_id: int
    check_time: datetime
    raw_response: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

# Purchase attempt schemas
class PurchaseAttemptBase(BaseModel):
    status: str
    error_message: Optional[str] = None
    transaction_id: Optional[str] = None

class PurchaseAttemptCreate(PurchaseAttemptBase):
    task_id: int
    raw_response: Optional[Dict[str, Any]] = None

class PurchaseAttempt(PurchaseAttemptBase):
    id: int
    task_id: int
    attempt_time: datetime
    raw_response: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True) 