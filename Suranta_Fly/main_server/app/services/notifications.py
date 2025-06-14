import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Dict, Any
import json
from contextlib import contextmanager

from ..core.config import settings
from ..database import SessionLocal
from .. import crud

logger = logging.getLogger(__name__)

@contextmanager
def get_db():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def send_notification(user_id: int, notification_data: Dict[str, Any]):
    """Send notification to user through configured channels."""
    with get_db() as db:
        user = crud.get_user(db, user_id)
        if not user:
            logger.error(f"User {user_id} not found for notification")
            return
        
        # Get user's notification settings
        task = crud.get_monitoring_task(db, notification_data["task_id"])
        if not task:
            logger.error(f"Task {notification_data['task_id']} not found for notification")
            return
        
        notification_settings = task.notification_settings
        
        # Send email if enabled
        if settings.ENABLE_EMAIL_NOTIFICATIONS and notification_settings.get("email", True):
            send_email_notification(user.email, notification_data)
        
        # Log notification
        logger.info(f"Notification sent to user {user_id}: {json.dumps(notification_data)}")

def send_email_notification(email: str, notification_data: Dict[str, Any]):
    """Send email notification."""
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USERNAME
        msg["To"] = email
        msg["Subject"] = get_email_subject(notification_data)
        
        body = get_email_body(notification_data)
        msg.attach(MIMEText(body, "html"))
        
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
    except Exception as e:
        logger.error(f"Error sending email notification: {str(e)}")
        raise

def get_email_subject(notification_data: Dict[str, Any]) -> str:
    """Generate email subject based on notification type."""
    if notification_data["type"] == "flight_available":
        return f"Flight Available: {notification_data['flight_number']} - {notification_data['origin']} to {notification_data['destination']}"
    elif notification_data["type"] == "purchase_result":
        status = "Success" if notification_data["success"] else "Failed"
        return f"Purchase {status}: Flight {notification_data['task_id']}"
    else:
        return "Flight Monitoring Notification"

def get_email_body(notification_data: Dict[str, Any]) -> str:
    """Generate HTML email body based on notification type."""
    if notification_data["type"] == "flight_available":
        return f"""
        <html>
            <body>
                <h2>Flight Available!</h2>
                <p>Flight {notification_data['flight_number']} is now available:</p>
                <ul>
                    <li>From: {notification_data['origin']}</li>
                    <li>To: {notification_data['destination']}</li>
                    <li>Date: {notification_data['departure_date']}</li>
                    <li>Price: ${notification_data.get('price', 'N/A')}</li>
                    <li>Seats Available: {notification_data.get('seats_available', 'N/A')}</li>
                </ul>
                <p>Please check your dashboard for more details.</p>
            </body>
        </html>
        """
    elif notification_data["type"] == "purchase_result":
        return f"""
        <html>
            <body>
                <h2>Purchase {'Successful' if notification_data['success'] else 'Failed'}</h2>
                <p>Transaction ID: {notification_data.get('transaction_id', 'N/A')}</p>
                {f"<p>Error: {notification_data['error_message']}</p>" if not notification_data['success'] else ""}
                <p>Please check your dashboard for more details.</p>
            </body>
        </html>
        """
    else:
        return f"""
        <html>
            <body>
                <h2>Flight Monitoring Notification</h2>
                <p>Please check your dashboard for details.</p>
            </body>
        </html>
        """ 