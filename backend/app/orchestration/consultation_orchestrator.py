"""
Consultation Orchestrator

Main orchestrator that coordinates execution of all agents.
Handles dependency management, parallel execution, consensus building, result persistence, and error recovery.
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents import BaseAgent, AgentContext
from app.communication import AgentCommunicationLayer, EventType, create_agent_event
from app.models import (
    AgentProcessingReport, AgentEventLog,
    AgentRecommendation, EscalationEvent, AgentConsensus,
    AgentEventType, EscalationLevel
)
from app.orchestration.workflow_coordinator import WorkflowCoordinator
from app.orchestration.consensus_engine import ConsensusEngine

logger = logging.getLogger(__name__)


class ConsultationOrchestrator:
    """
    Orchestrates agent execution for a consultation.
    Manages: sequencing, parallelization, dependency resolution, consensus, persistence, error recovery.
    """
    
    MAX_RETRIES = 2
    TIMEOUT_SECONDS = 35
    
    def __init__(
        self,
        agents: Dict[str, BaseAgent],
        communication_layer: AgentCommunicationLayer,
        db: AsyncSession,
        memory_manager: Optional[Any] = None
    ):
        self.agents = agents
        self.communication = communication_layer
        self.db = db
        self.memory_manager = memory_manager
    
    async def process_consultation(
        self,
        consultation_id: str,
        context: AgentContext
    ) -> Dict[str, Any]:
        """
        Main processing pipeline with error recovery and persistence.
        
        Returns: {
            status: COMPLETED|FAILED,
            processing_report: AgentProcessingReport,
            agent_outputs: {agent_type: result},
            consensus: consensus_result,
            duration_seconds: float
        }
        """
        
        start_time = time.time()
        processing_report = None
        agent_outputs = {}
        escalations = []
        
        try:
            processing_report = AgentProcessingReport(
                consultation_id=consultation_id,
                started_at=datetime.utcnow(),
                processing_status="PROCESSING"
            )
            self.db.add(processing_report)
            await self.db.flush()
            
            logger.info(f"Starting agent orchestration for consultation {consultation_id}")
            
            execution_plan = self._build_execution_plan()
            
            for batch_index, execution_batch in enumerate(execution_plan):
                logger.debug(f"Executing batch {batch_index + 1}: {execution_batch}")
                
                try:
                    batch_results = await asyncio.gather(
                        *[
                            self._execute_agent_with_retry(
                                agent_type,
                                context,
                                processing_report.id,
                                consultation_id
                            )
                            for agent_type in execution_batch
                        ],
                        return_exceptions=True
                    )
                    
                    for agent_type, result in zip(execution_batch, batch_results):
                        if isinstance(result, Exception):
                            logger.error(f"Agent {agent_type} failed: {result}")
                            agent_outputs[agent_type] = {
                                "status": "FAILED",
                                "error": str(result)
                            }
                        else:
                            agent_outputs[agent_type] = result
                            escalations.extend(result.get("escalations", []))
                            await self._record_to_memory(consultation_id, agent_type, result)
                
                except Exception as e:
                    logger.error(f"Batch {batch_index} execution error: {e}")
                    continue
            
            consensus = await self._build_consensus(
                agent_outputs,
                processing_report.id,
                consultation_id
            )
            
            await self._persist_results(
                processing_report.id,
                agent_outputs,
                consensus,
                escalations
            )
            
            # Emit consensus update event for real-time dashboard
            if self.communication:
                consensus_event = create_agent_event(
                    event_type=EventType.CONSENSUS_UPDATE,
                    source_agent="ConsensusEngine",
                    source_agent_id="consensus-engine",
                    consultation_id=consultation_id,
                    payload={
                        "consensus_score": consensus.get("consensus_score", 0.0),
                        "risk_score": consensus.get("overall_risk_score", 0.0),
                        "recommendations": consensus.get("final_recommendations", []),
                        "primary_diagnosis": consensus.get("primary_diagnosis")
                    }
                )
                await self.communication.publish(consensus_event)
            
            duration = time.time() - start_time
            processing_report.completed_at = datetime.utcnow()
            processing_report.total_duration_seconds = duration
            processing_report.processing_status = "COMPLETED"
            processing_report.agents_executed = [a for a in agent_outputs.keys() if agent_outputs[a].get("status") == "COMPLETED"]
            processing_report.agents_failed = [a for a in agent_outputs.keys() if agent_outputs[a].get("status") == "FAILED"]
            processing_report.consensus_score = consensus.get("consensus_score", 0.0)
            processing_report.overall_risk_score = consensus.get("overall_risk_score", 0.0)
            processing_report.escalation_triggered = len(escalations) > 0
            
            if escalations:
                try:
                    levels = [EscalationLevel[e.get("level", "LOW")] for e in escalations]
                    processing_report.escalation_level = max(levels) if levels else None
                except (KeyError, ValueError):
                    pass
            
            self.db.add(processing_report)
            await self.db.commit()
            
            logger.info(f"Consultation processing completed in {duration:.2f}s")
            
            return {
                "status": "COMPLETED",
                "processing_report": processing_report,
                "agent_outputs": agent_outputs,
                "consensus": consensus,
                "duration_seconds": duration
            }
        
        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            
            try:
                if processing_report:
                    processing_report.processing_status = "FAILED"
                    processing_report.error_message = str(e)
                    processing_report.completed_at = datetime.utcnow()
                    self.db.add(processing_report)
                    await self.db.commit()
            except Exception as persist_error:
                logger.error(f"Failed to persist error state: {persist_error}")
            
            return {
                "status": "FAILED",
                "error": str(e),
                "duration_seconds": time.time() - start_time
            }
    
    async def _record_to_memory(self, consultation_id: str, agent_type: str, result: Dict[str, Any]) -> None:
        if not self.memory_manager:
            return
        try:
            await self.memory_manager.consultation_memory.record_agent_output(consultation_id, agent_type, result)
            top_rec = next(iter(result.get("recommendations", [])), None)
            if top_rec:
                await self.memory_manager.shared_memory.write(
                    consultation_id, f"{agent_type.lower()}_top_recommendation", top_rec.get("text")
                )
        except Exception as e:
            logger.warning(f"Memory recording failed for {agent_type} (non-fatal): {e}")

    def _build_execution_plan(self) -> List[List[str]]:
        """
        Build execution plan with dependency resolution across the full
        agent roster (original 7 + the 10 added in V2), filtered down to
        whatever agents are actually registered so a partially-configured
        registry still runs instead of deadlocking.
        """
        full_plan = WorkflowCoordinator.default_plan()
        available = set(self.agents.keys())

        filtered_plan = []
        for batch in full_plan:
            filtered_batch = [agent_type for agent_type in batch if agent_type in available]
            if filtered_batch:
                filtered_plan.append(filtered_batch)

        return filtered_plan or [list(available)]
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def _execute_agent_with_retry(
        self,
        agent_type: str,
        context: AgentContext,
        report_id: str,
        consultation_id: str
    ) -> Dict[str, Any]:
        """Execute agent with automatic retry on failure"""
        
        try:
            if agent_type not in self.agents:
                return {"status": "SKIPPED", "reason": f"Agent {agent_type} not available"}
            
            agent = self.agents[agent_type]
            
            result = await asyncio.wait_for(
                agent.execute(context),
                timeout=agent.TIMEOUT_SECONDS
            )
            
            return result
        
        except asyncio.TimeoutError:
            logger.warning(f"Agent {agent_type} timeout")
            raise
        except Exception as e:
            logger.warning(f"Agent {agent_type} error: {e}")
            raise
    
    async def _build_consensus(
        self,
        agent_outputs: Dict[str, Dict],
        report_id: str,
        consultation_id: str
    ) -> Dict[str, Any]:
        """
        Build real consensus from agent outputs. Delegates the actual
        scoring to ConsensusEngine (unit-testable in isolation) and folds in
        the Consensus Moderator agent's rulings, if that agent ran, so its
        tie-breaks outrank a naive highest-confidence pick.
        """
        moderator_rulings = []
        try:
            history = await self.communication.get_event_history(consultation_id, limit=200)
            for event in reversed(history):
                if event.event_type == EventType.MODERATOR_DECISION:
                    moderator_rulings = event.payload.get("rulings", [])
                    break
        except Exception as e:
            logger.warning(f"Could not read moderator decision for consensus: {e}")

        vision_observation = None
        if self.memory_manager:
            try:
                vision_summary = await self.memory_manager.shared_memory.read(
                    consultation_id, "latest_vision_observation"
                )
                if vision_summary:
                    vision_observation = {"summary": vision_summary}
            except Exception as e:
                logger.warning(f"Could not read vision observation for consensus: {e}")

        total_agents = len(self.agents) or 7
        engine = ConsensusEngine(total_agents=total_agents)
        return engine.build_consensus(
            agent_outputs, moderator_rulings=moderator_rulings, vision_observation=vision_observation
        )
    
    async def _persist_results(
        self,
        report_id: str,
        agent_outputs: Dict[str, Dict],
        consensus: Dict[str, Any],
        escalations: List[Dict]
    ):
        """Persist all agent outputs and consensus to database with full transaction support"""
        
        try:
            report_result = await self.db.execute(
                select(AgentProcessingReport).where(AgentProcessingReport.id == report_id)
            )
            report = report_result.scalar_one_or_none()
            
            if not report:
                logger.error(f"Report {report_id} not found for persistence")
                return
            
            report.master_recommendations = [
                {
                    "text": r.get("text", ""),
                    "type": r.get("type", ""),
                    "confidence": r.get("weighted_confidence", 0.7),
                    "source": r.get("source_agent", "")
                }
                for r in consensus.get("final_recommendations", [])
            ]
            report.overall_risk_score = consensus.get("overall_risk_score", 0.0)
            report.consensus_score = consensus.get("consensus_score", 0.0)
            report.critical_alerts = [
                rec.get("text", "") for rec in consensus.get("final_recommendations", [])
                if rec.get("priority") == "CRITICAL"
            ]
            
            for agent_type, output in agent_outputs.items():
                if output.get("status") != "COMPLETED":
                    continue
                
                agent_event = AgentEventLog(
                    processing_report_id=report_id,
                    agent_type=agent_type,
                    agent_id=output.get("agent_id", "unknown"),
                    event_type=AgentEventType.AGENT_COMPLETED,
                    status="COMPLETED",
                    duration_ms=output.get("duration_ms", 0),
                    confidence_score=output.get("confidence", 0.8),
                    reasoning=str(output.get("metadata", {})),
                    agent_output=output.get("metadata", {})
                )
                self.db.add(agent_event)
                await self.db.flush()
                
                for rec in output.get("recommendations", []):
                    recommendation = AgentRecommendation(
                        processing_report_id=report_id,
                        agent_event_id=agent_event.id,
                        source_agent=agent_type,
                        source_agent_id=output.get("agent_id", "unknown"),
                        recommendation_type=rec.get("type", "general"),
                        recommendation_text=rec.get("text", ""),
                        recommendation_data=rec,
                        confidence_score=rec.get("confidence", 0.7),
                        priority=rec.get("priority", "MEDIUM"),
                        supporting_evidence=rec.get("evidence", []),
                        reasoning=rec.get("reasoning", "")
                    )
                    self.db.add(recommendation)
            
            for escalation in escalations:
                try:
                    escalation_level = EscalationLevel[escalation.get("level", "LOW")]
                except (KeyError, ValueError):
                    escalation_level = EscalationLevel.LOW
                
                escalation_event = EscalationEvent(
                    processing_report_id=report_id,
                    escalation_level=escalation_level,
                    escalation_reason=escalation.get("reason", "")[:255],
                    escalation_type=escalation.get("type", "unknown"),
                    triggered_by_agent=escalation.get("source_agent", "UNKNOWN"),
                    triggered_by_agent_id="system",
                    details=escalation,
                    required_action=escalation.get("action", "")
                )
                self.db.add(escalation_event)
            
            risk_level = EscalationLevel.LOW
            if consensus.get("overall_risk_score", 0) >= 0.8:
                risk_level = EscalationLevel.CRITICAL
            elif consensus.get("overall_risk_score", 0) >= 0.6:
                risk_level = EscalationLevel.HIGH
            elif consensus.get("overall_risk_score", 0) >= 0.4:
                risk_level = EscalationLevel.MEDIUM
            
            consensus_record = AgentConsensus(
                processing_report_id=report_id,
                total_agents_executed=consensus.get("total_agents_executed", 0),
                total_agents_agreed=consensus.get("total_agents_agreed", 0),
                consensus_percentage=consensus.get("consensus_score", 0.0) * 100,
                primary_diagnosis=consensus.get("primary_diagnosis"),
                risk_level=risk_level,
                risk_factors=consensus.get("risk_factors", []),
                agent_agreements=consensus.get("agent_agreements", {}),
                conflicting_recommendations=[c.get("description", "") for c in consensus.get("conflicts", [])],
                final_recommendations=[r.get("text", "") for r in consensus.get("final_recommendations", [])],
                requires_doctor_review=consensus.get("requires_doctor_review", True)
            )
            self.db.add(consensus_record)
            
            await self.db.commit()
            logger.info(f"Successfully persisted results for report {report_id}")
            
        except Exception as e:
            logger.error(f"Error persisting results: {e}", exc_info=True)
            try:
                await self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")