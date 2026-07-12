"""
GestureMed AI — AI Reports API
Triggers and retrieves AI-generated consultation reports.
Uses Celery for non-blocking generation; FastAPI BackgroundTasks as fallback.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import json
import io

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user
from app.models import User, AIReport, Consultation, GestureEvent, Annotation, ReportStatus
from app.services.ai.report_generator import AIReportService

router = APIRouter()


async def _generate_and_save_report(consultation_id: str) -> None:
    """
    Self-contained async report generator with its own DB session.
    Called from BackgroundTasks — must NOT share the request session.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            return

        ann_result = await db.execute(
            select(Annotation).where(Annotation.consultation_id == consultation_id)
        )
        annotations = [
            {"body_region": a.body_region, "note": a.note, "type": a.annotation_type}
            for a in ann_result.scalars()
        ]

        gest_result = await db.execute(
            select(GestureEvent).where(GestureEvent.consultation_id == consultation_id)
        )
        gesture_events = [
            {"action_taken": e.action_taken, "gesture_type": e.gesture_type}
            for e in gest_result.scalars()
        ]

        service = AIReportService()
        report_data = await service.generate_report(
            consultation_id=consultation_id,
            doctor_notes=consultation.doctor_notes,
            patient_chief_complaint=consultation.chief_complaint,
            annotations=annotations,
            gesture_events=gesture_events,
            duration_seconds=consultation.duration_seconds,
        )

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


@router.post("/{consultation_id}/generate", status_code=202)
async def generate_report(
    consultation_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI report generation for a completed consultation."""
    result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consultation = result.scalar_one_or_none()
    if not consultation:
        raise HTTPException(404, "Consultation not found")

    # Check for existing report
    report_result = await db.execute(
        select(AIReport).where(AIReport.consultation_id == consultation_id)
    )
    existing = report_result.scalar_one_or_none()

    if existing and existing.status == ReportStatus.COMPLETED:
        return {"status": "already_complete", "report_id": existing.id}

    if not existing:
        report = AIReport(
            consultation_id=consultation_id,
            status=ReportStatus.GENERATING,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        report_id = report.id
    else:
        existing.status = ReportStatus.GENERATING
        await db.commit()
        report_id = existing.id

    # Try Celery first, fall back to FastAPI background task
    try:
        from app.tasks.report_tasks import generate_consultation_report
        generate_consultation_report.delay(consultation_id)
    except Exception:
        background_tasks.add_task(_generate_and_save_report, consultation_id)

    return {"status": "generating", "report_id": report_id}


@router.get("/{consultation_id}")
async def get_report(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIReport).where(AIReport.consultation_id == consultation_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found. Trigger generation first.")

    return {
        "id": report.id,
        "consultation_id": consultation_id,
        "status": report.status,
        "summary": report.summary,
        "symptoms_observed": report.symptoms_observed,
        "areas_marked": report.areas_marked,
        "suggested_next_steps": report.suggested_next_steps,
        "risk_indicators": report.risk_indicators,
        "structured_data": report.structured_data,
        "generated_at": report.generated_at,
        "created_at": report.created_at,
    }


@router.get("/")
async def list_my_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all AI reports accessible to the current user."""
    from app.models import PatientProfile, DoctorProfile

    if current_user.role.value == "PATIENT":
        patient_result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == current_user.id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient:
            return []
        consult_result = await db.execute(
            select(Consultation.id).where(Consultation.patient_id == patient.id)
        )
        consultation_ids = [row[0] for row in consult_result]
    elif current_user.role.value == "DOCTOR":
        doctor_result = await db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            return []
        consult_result = await db.execute(
            select(Consultation.id).where(Consultation.doctor_id == doctor.id)
        )
        consultation_ids = [row[0] for row in consult_result]
    else:
        consult_result = await db.execute(select(Consultation.id))
        consultation_ids = [row[0] for row in consult_result]

    if not consultation_ids:
        return []

    report_result = await db.execute(
        select(AIReport)
        .where(AIReport.consultation_id.in_(consultation_ids))
        .order_by(AIReport.created_at.desc())
    )
    reports = report_result.scalars().all()
    return [
        {
            "id": r.id,
            "consultation_id": r.consultation_id,
            "status": r.status,
            "summary": r.summary,
            "generated_at": r.generated_at,
            "created_at": r.created_at,
        }
        for r in reports
    ]


def _report_to_markdown(report: AIReport, consultation_id: str) -> str:
    lines = [
        f"# Consultation Report - {consultation_id}",
        "",
        f"**Status:** {report.status}",
        f"**Generated:** {report.generated_at.isoformat() if report.generated_at else 'pending'}",
        "",
        "## Summary",
        report.summary or "No summary available.",
        "",
        "## Symptoms Observed",
    ]
    for s in (report.symptoms_observed or []):
        lines.append(f"- {s}")
    lines += ["", "## Areas Marked"]
    for a in (report.areas_marked or []):
        lines.append(f"- {a}")
    lines += ["", "## Suggested Next Steps"]
    for step in (report.suggested_next_steps or []):
        lines.append(f"- {step}")
    lines += ["", "## Risk Indicators"]
    for r in (report.risk_indicators or []):
        lines.append(f"- {r}")
    return "\n".join(lines)


def _report_to_pdf_bytes(report: AIReport, consultation_id: str) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Consultation Report - {consultation_id}", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Status: {report.status}", styles["Normal"]),
        Paragraph(f"Generated: {report.generated_at.isoformat() if report.generated_at else 'pending'}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Summary", styles["Heading2"]),
        Paragraph(report.summary or "No summary available.", styles["Normal"]),
        Spacer(1, 12),
    ]

    def _section(title: str, items):
        story.append(Paragraph(title, styles["Heading2"]))
        if items:
            story.append(ListFlowable([ListItem(Paragraph(str(i), styles["Normal"])) for i in items]))
        else:
            story.append(Paragraph("None recorded.", styles["Normal"]))
        story.append(Spacer(1, 12))

    _section("Symptoms Observed", report.symptoms_observed or [])
    _section("Areas Marked", report.areas_marked or [])
    _section("Suggested Next Steps", report.suggested_next_steps or [])
    _section("Risk Indicators", report.risk_indicators or [])

    doc.build(story)
    return buffer.getvalue()


@router.get("/{consultation_id}/export/{export_format}")
async def export_report(
    consultation_id: str,
    export_format: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export a generated report as markdown, json, or pdf."""
    export_format = export_format.lower()
    if export_format not in ("markdown", "md", "json", "pdf"):
        raise HTTPException(400, "export_format must be one of: markdown, json, pdf")

    result = await db.execute(select(AIReport).where(AIReport.consultation_id == consultation_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found. Trigger generation first.")

    if export_format in ("markdown", "md"):
        content = _report_to_markdown(report, consultation_id)
        return Response(content=content, media_type="text/markdown", headers={
            "Content-Disposition": f'attachment; filename="report-{consultation_id}.md"'
        })

    if export_format == "json":
        payload = {
            "consultation_id": consultation_id,
            "status": report.status.value if hasattr(report.status, "value") else report.status,
            "summary": report.summary,
            "symptoms_observed": report.symptoms_observed,
            "areas_marked": report.areas_marked,
            "suggested_next_steps": report.suggested_next_steps,
            "risk_indicators": report.risk_indicators,
            "structured_data": report.structured_data,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        }
        return Response(
            content=json.dumps(payload, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="report-{consultation_id}.json"'},
        )

    # pdf
    pdf_bytes = _report_to_pdf_bytes(report, consultation_id)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="report-{consultation_id}.pdf"'
    })
