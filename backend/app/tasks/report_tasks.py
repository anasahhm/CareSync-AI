"""
GestureMed AI — Celery Report Tasks
Async AI report generation triggered after consultation ends.
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.report_tasks.generate_consultation_report",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def generate_consultation_report(self, consultation_id: str):
    """
    Generate AI report for a completed consultation.
    Runs in Celery worker process — uses its own sync DB session.
    """
    try:
        asyncio.run(_async_generate(consultation_id))
    except Exception as exc:
        logger.error(f"Report generation failed for {consultation_id}: {exc}")
        raise self.retry(exc=exc)


async def _async_generate(consultation_id: str):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.models import Consultation, AIReport, Annotation, GestureEvent, ReportStatus
    from app.services.ai.report_generator import AIReportService

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # Fetch consultation
        result = await db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            logger.warning(f"Consultation {consultation_id} not found for report generation")
            return

        # Fetch annotations
        ann_result = await db.execute(
            select(Annotation).where(Annotation.consultation_id == consultation_id)
        )
        annotations = [
            {"body_region": a.body_region, "note": a.note, "type": a.annotation_type}
            for a in ann_result.scalars()
        ]

        # Fetch gesture events
        gest_result = await db.execute(
            select(GestureEvent).where(GestureEvent.consultation_id == consultation_id)
        )
        gesture_events = [
            {"action_taken": e.action_taken, "gesture_type": e.gesture_type}
            for e in gest_result.scalars()
        ]

        # Generate AI report
        service = AIReportService()
        report_data = await service.generate_report(
            consultation_id=consultation_id,
            doctor_notes=consultation.doctor_notes,
            patient_chief_complaint=consultation.chief_complaint,
            annotations=annotations,
            gesture_events=gesture_events,
            duration_seconds=consultation.duration_seconds,
        )

        # Save or update report
        report_result = await db.execute(
            select(AIReport).where(AIReport.consultation_id == consultation_id)
        )
        report = report_result.scalar_one_or_none()

        if report:
            report.structured_data = report_data
            report.summary = report_data.get("summary")
            report.symptoms_observed = report_data.get("symptoms_observed", [])
            report.areas_marked = report_data.get("areas_marked", [])
            report.suggested_next_steps = report_data.get("suggested_next_steps", [])
            report.risk_indicators = report_data.get("risk_indicators", [])
            report.status = ReportStatus.COMPLETED
            report.generated_at = datetime.utcnow()
        else:
            report = AIReport(
                consultation_id=consultation_id,
                status=ReportStatus.COMPLETED,
                structured_data=report_data,
                summary=report_data.get("summary"),
                symptoms_observed=report_data.get("symptoms_observed", []),
                areas_marked=report_data.get("areas_marked", []),
                suggested_next_steps=report_data.get("suggested_next_steps", []),
                risk_indicators=report_data.get("risk_indicators", []),
                generated_at=datetime.utcnow(),
            )
            db.add(report)

        await db.commit()
        logger.info(f"AI report generated successfully for consultation {consultation_id}")

    await engine.dispose()
