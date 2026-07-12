"""
GestureMed AI — AI Report Generation Service

Generates structured medical consultation reports using LLM.
Runs as a Celery task for non-blocking operation.

DISCLAIMER: AI-generated assistance only. Not a final medical diagnosis.
"""
import json
import logging
from datetime import datetime
from typing import Optional
import httpx

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from app.core.config import settings
from app.gpu.model_loader import ModelLoader
from app.gpu.device_manager import DeviceManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI medical documentation assistant for GestureMed AI, 
a telemedicine platform. Your role is to generate structured consultation summaries 
based on doctor notes, patient-reported symptoms, and body annotation data.

CRITICAL DISCLAIMER: You are an AI assistant. Your output is documentation aid ONLY. 
It is NOT a medical diagnosis and should NEVER replace professional medical judgment.
Always include the disclaimer in every report.

Generate reports in valid JSON format matching the specified schema exactly.
Be precise, clinical, and factual. Use medical terminology appropriately.
Flag any concerning patterns as risk indicators (never diagnose).
"""

REPORT_SCHEMA = """
{
  "summary": "2-3 sentence consultation overview",
  "symptoms_observed": ["list of symptoms mentioned"],
  "areas_marked": ["list of body areas annotated by doctor"],
  "doctor_assessment_notes": "summary of doctor notes",
  "patient_complaints": ["list of patient-reported issues"],
  "suggested_next_steps": ["actionable follow-up items"],
  "risk_indicators": ["any patterns warranting attention — NOT diagnoses"],
  "follow_up_recommendation": "suggested timeframe for follow-up",
  "ai_disclaimer": "AI-generated assistance only. Not a final medical diagnosis. Consult your healthcare provider for medical advice."
}
"""


class AIReportService:
    """LLM-powered consultation report generator."""

    def __init__(self):
        provider = settings.AI_PROVIDER.lower().strip()

        self._llm = None
        self._use_gemini = False

        if provider == "gemini" and settings.GEMINI_API_KEY:
            self._use_gemini = True

        elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            self._llm = ChatAnthropic(
                model=settings.AI_MODEL,
                api_key=settings.ANTHROPIC_API_KEY,
                max_tokens=2000,
            )

        elif provider == "openai" and settings.OPENAI_API_KEY:
            self._llm = ChatOpenAI(
                model=settings.AI_MODEL or "gpt-4o",
                api_key=settings.OPENAI_API_KEY,
                max_tokens=2000,
            )

        elif settings.GEMINI_API_KEY:
            # Helpful fallback:
            # If GEMINI_API_KEY exists but AI_PROVIDER was accidentally left as default,
            # still use Gemini instead of falling all the way to Ollama/stub.
            self._use_gemini = True

        elif settings.ANTHROPIC_API_KEY:
            self._llm = ChatAnthropic(
                model=settings.AI_MODEL,
                api_key=settings.ANTHROPIC_API_KEY,
                max_tokens=2000,
            )

        elif settings.OPENAI_API_KEY:
            self._llm = ChatOpenAI(
                model=settings.AI_MODEL or "gpt-4o",
                api_key=settings.OPENAI_API_KEY,
                max_tokens=2000,
            )

        else:
            logger.info(
                "No cloud AI provider (Anthropic/OpenAI/Gemini) configured; will attempt free local "
                "generation via Ollama before falling back to the minimal stub report."
            )

        # Free/local fallback path - used whenever no paid LLM is configured,
        # or if the paid/cloud call fails at runtime.
        self._model_loader = ModelLoader(
            device_manager=DeviceManager(preferred_backend=settings.GPU_BACKEND),
            ollama_url=settings.OLLAMA_URL,
            ollama_fallback_model=settings.OLLAMA_FALLBACK_MODEL,
        )

    async def generate_report(
        self,
        consultation_id: str,
        doctor_notes: Optional[str],
        patient_chief_complaint: Optional[str],
        annotations: list,
        gesture_events: list,
        duration_seconds: Optional[int],
    ) -> dict:
        """
        Generate a structured AI report from consultation data.
        Returns a dict matching REPORT_SCHEMA.
        """
        # Build context (shared by both the paid-LLM and free-model paths)
        context = self._build_context(
            doctor_notes=doctor_notes,
            chief_complaint=patient_chief_complaint,
            annotations=annotations,
            gesture_events=gesture_events,
            duration_seconds=duration_seconds,
        )

        if self._use_gemini:
            return await self._generate_via_gemini(consultation_id, context)

        if not self._llm:
            return await self._generate_via_free_model(consultation_id, context)

        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"""
Generate a structured medical consultation report for the following session.
Return ONLY valid JSON matching this schema (no markdown, no preamble):

{REPORT_SCHEMA}

Consultation Data:
{context}
"""),
            ]

            response = await self._llm.ainvoke(messages)
            return self._parse_report_json(response.content, consultation_id)

        except json.JSONDecodeError as e:
            logger.error(f"AI report JSON parse error: {e}")
            return await self._generate_via_free_model(consultation_id, context, prior_error=str(e))
        except Exception as e:
            logger.error(f"AI report generation failed: {e}")
            return await self._generate_via_free_model(consultation_id, context, prior_error=str(e))

    async def _generate_via_gemini(self, consultation_id: str, context: str) -> dict:
        """Generate report through Google's Gemini generateContent REST API."""
        prompt = f"""Generate a structured medical consultation report for the following session.
    Return ONLY valid JSON matching this schema (no markdown, no preamble):

    {REPORT_SCHEMA}

    Consultation Data:
    {context}
    """

        model = settings.AI_MODEL.strip()

        # Allow both "gemini-2.5-flash" and "models/gemini-2.5-flash"
        if model.startswith("models/"):
            model = model.removeprefix("models/")

        # Safety fallback in case AI_MODEL is still set to Claude/GPT model name
        if not model.startswith("gemini"):
            model = "gemini-3.5-flash"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2000,
                "responseMimeType": "application/json",
            },
        }

        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": settings.GEMINI_API_KEY,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code >= 400:
                    logger.error(f"Gemini API error {response.status_code}: {response.text}")

                response.raise_for_status()

            data = response.json()

            parts = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            )

            text = "".join(part.get("text", "") for part in parts).strip()

            if not text:
                raise ValueError("Gemini response did not contain report text")

            return self._parse_report_json(text, consultation_id)

        except json.JSONDecodeError as e:
            logger.error(f"Gemini report JSON parse error: {e}")
            return await self._generate_via_free_model(
                consultation_id,
                context,
                prior_error=str(e),
            )

        except Exception as e:
            logger.error(f"Gemini report generation failed: {e}")
            return await self._generate_via_free_model(
                consultation_id,
                context,
                prior_error=str(e),
            )


    def _parse_report_json(self, raw_content: str, consultation_id: str) -> dict:
        content = raw_content.strip()

        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]

        report_data = json.loads(content.strip())
        report_data["consultation_id"] = consultation_id
        report_data["generated_at"] = datetime.utcnow().isoformat()
        return report_data

    async def _generate_via_free_model(self, consultation_id: str, context: str, prior_error: Optional[str] = None) -> dict:
        """
        Free/local generation path via Ollama (ModelLoader), used when no paid
        LLM is configured, or as a second-tier fallback if the paid call
        itself failed. Only falls through to the empty stub report if Ollama
        is also unreachable - so a fully free/local deployment still gets
        real generated reports, not just an empty placeholder.
        """
        prompt = f"""{SYSTEM_PROMPT}

Generate a structured medical consultation report for the following session.
Return ONLY valid JSON matching this schema (no markdown, no preamble):

{REPORT_SCHEMA}

Consultation Data:
{context}
"""
        try:
            result = await self._model_loader.generate(prompt)
            if result.get("backend") == "ollama" and result.get("text"):
                return self._parse_report_json(result["text"], consultation_id)

            logger.info(
                f"Free-model report generation unavailable ({result.get('note', 'no backend reachable')}); "
                f"returning minimal stub report."
            )
            return self._stub_report(consultation_id, error=prior_error)
        except json.JSONDecodeError as e:
            logger.error(f"Free-model report JSON parse error: {e}")
            return self._stub_report(consultation_id, error=str(e))
        except Exception as e:
            logger.error(f"Free-model report generation failed: {e}")
            return self._stub_report(consultation_id, error=prior_error or str(e))

    def _build_context(
        self,
        doctor_notes: Optional[str],
        chief_complaint: Optional[str],
        annotations: list,
        gesture_events: list,
        duration_seconds: Optional[int],
    ) -> str:
        lines = []

        if duration_seconds:
            mins = duration_seconds // 60
            lines.append(f"Consultation Duration: {mins} minutes")

        if chief_complaint:
            lines.append(f"Patient Chief Complaint: {chief_complaint}")

        if doctor_notes:
            lines.append(f"Doctor Notes: {doctor_notes}")

        if annotations:
            regions = [a.get("body_region") or a.get("note", "unspecified") for a in annotations]
            lines.append(f"Body Areas Annotated: {', '.join(r for r in regions if r)}")

        # Extract pain events from gestures
        pain_events = [
            e for e in gesture_events
            if (e.get("action_taken") or "").startswith("PAIN_")
        ]
        if pain_events:
            max_pain = max(
                int(e["action_taken"].split("_")[1])
                for e in pain_events
                if e.get("action_taken") and e["action_taken"].split("_")[-1].isdigit()
            )
            lines.append(f"Peak Patient-Reported Pain Level: {max_pain}/5")

        nurse_calls = [e for e in gesture_events if e.get("action_taken") == "NURSE_CALLED"]
        if nurse_calls:
            lines.append(f"Nurse Called: {len(nurse_calls)} time(s)")

        emergency_events = [e for e in gesture_events if e.get("action_taken") == "EMERGENCY"]
        if emergency_events:
            lines.append("EMERGENCY GESTURE DETECTED during consultation")

        return "\n".join(lines) if lines else "Minimal consultation data recorded."

    def _stub_report(self, consultation_id: str, error: Optional[str] = None) -> dict:
        """Fallback report when AI is unavailable."""
        return {
            "consultation_id": consultation_id,
            "summary": "Consultation completed. AI report generation was unavailable.",
            "symptoms_observed": [],
            "areas_marked": [],
            "doctor_assessment_notes": "See doctor notes.",
            "patient_complaints": [],
            "suggested_next_steps": ["Schedule follow-up appointment"],
            "risk_indicators": [],
            "follow_up_recommendation": "As recommended by treating physician",
            "ai_disclaimer": "AI-generated assistance only. Not a final medical diagnosis. Consult your healthcare provider for medical advice.",
            "generated_at": datetime.utcnow().isoformat(),
            "error": error,
        }


# Singleton
_report_service: Optional[AIReportService] = None


def get_report_service() -> AIReportService:
    global _report_service
    if _report_service is None:
        _report_service = AIReportService()
    return _report_service
