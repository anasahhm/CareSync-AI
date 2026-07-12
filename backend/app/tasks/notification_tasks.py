"""
GestureMed AI — Celery Notification Tasks
Email / push notification dispatch for medical events.
"""
import logging
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.notification_tasks.send_nurse_alert")
def send_nurse_alert(patient_id: str, room_id: str, message: str):
    """Notify nursing staff of a patient gesture alert."""
    logger.info(f"[NURSE ALERT] Patient {patient_id} in room {room_id}: {message}")
    # Production: integrate with hospital notification system (paging, SMS, push)


@celery_app.task(name="app.tasks.notification_tasks.send_emergency_alert")
def send_emergency_alert(patient_id: str, room_id: str):
    """Broadcast emergency alert to all on-duty staff."""
    logger.critical(f"[EMERGENCY] Patient {patient_id} in room {room_id} triggered emergency gesture")
    # Production: integrate with hospital code system


@celery_app.task(name="app.tasks.notification_tasks.send_report_ready")
def send_report_ready(patient_email: str, doctor_email: str, consultation_id: str):
    """Notify both parties that AI report is ready."""
    logger.info(f"[REPORT READY] Consultation {consultation_id} — notifying {patient_email}, {doctor_email}")
    # Production: send email via SendGrid / SES
