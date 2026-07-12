"""
Workflow Coordinator

Builds the batched execution plan (a list of lists of agent-type strings,
where each inner list can run concurrently) for the full agent roster -
the original 7 clinical/admin agents plus the 10 agents added in V2.

This replaces the previously-hardcoded 3-batch plan inside
ConsultationOrchestrator with a real dependency-driven topological sort, so
adding/removing an agent only requires updating DEPENDENCIES on the agent
class - nothing here needs to change by hand for simple cases.
"""
import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class WorkflowCoordinator:
    """
    Computes a topologically-sorted batch execution plan from each agent's
    `DEPENDENCIES` list. Agents not present in the registry (e.g. disabled
    via config) are skipped, and their absence does not block dependents -
    a missing dependency is treated as "already satisfied" so the pipeline
    degrades gracefully instead of deadlocking.
    """

    def __init__(self, agent_dependencies: Dict[str, List[str]]):
        """
        agent_dependencies: {agent_type: [dependency_agent_type, ...]}
        """
        self.agent_dependencies = agent_dependencies

    def build_execution_plan(self) -> List[List[str]]:
        remaining: Set[str] = set(self.agent_dependencies.keys())
        satisfied: Set[str] = set()
        plan: List[List[str]] = []

        max_iterations = len(remaining) + 1
        iterations = 0

        while remaining and iterations <= max_iterations:
            iterations += 1
            ready = {
                agent_type
                for agent_type in remaining
                if all(
                    dep in satisfied or dep not in self.agent_dependencies
                    for dep in self.agent_dependencies[agent_type]
                )
            }

            if not ready:
                # Circular or unresolvable dependency - break the cycle by
                # releasing whatever remains as a final batch rather than
                # hanging the whole consultation.
                logger.error(
                    f"Workflow coordinator detected unresolvable dependencies for: {remaining}. "
                    f"Releasing as final batch to avoid deadlock."
                )
                plan.append(sorted(remaining))
                break

            plan.append(sorted(ready))
            satisfied.update(ready)
            remaining -= ready

        return plan

    @classmethod
    def default_plan(cls) -> List[List[str]]:
        """
        The canonical V2 dependency graph for the full 17-agent roster.
        Kept as a class method (rather than only reading from live agent
        classes) so the plan is deterministic even if some agents are
        temporarily unavailable in the registry.
        """
        dependencies = {
            # Original 7
            "CLINICAL_REVIEW": [],
            "COMPLIANCE_PRIVACY": [],
            "INSURANCE_VERIFICATION": [],
            "MEDICAL_HISTORY": ["CLINICAL_REVIEW"],
            "TRIAGE_ESCALATION": ["CLINICAL_REVIEW"],
            "TREATMENT_RECOMMENDATION": ["MEDICAL_HISTORY", "TRIAGE_ESCALATION"],
            "FOLLOWUP_COORDINATION": ["TREATMENT_RECOMMENDATION", "TRIAGE_ESCALATION", "EXPLANATION", "ESCALATION"],
            # New 10 (V2)
            "CHIEF_ORCHESTRATOR": [],
            "SYMPTOM": [],
            "DIAGNOSTIC": ["SYMPTOM", "CLINICAL_REVIEW"],
            "MEDICAL_RESEARCH": ["DIAGNOSTIC"],
            "EVIDENCE": ["DIAGNOSTIC"],
            "HALLUCINATION_DETECTION": ["MEDICAL_RESEARCH", "EVIDENCE", "TREATMENT_RECOMMENDATION", "DIAGNOSTIC"],
            "QUALITY_ASSURANCE": ["HALLUCINATION_DETECTION"],
            "CONSENSUS_MODERATOR": ["QUALITY_ASSURANCE"],
            "EXPLANATION": ["CONSENSUS_MODERATOR"],
            "ESCALATION": ["CONSENSUS_MODERATOR"],
        }
        return cls(dependencies).build_execution_plan()
