"""Healthcare AI tools for the AgentForge agent system.

Nine LangChain-compatible tools covering drug interactions, symptoms,
providers, appointments, insurance, medications, and FDA recall monitoring.
"""

from app.tools.drug_interaction import drug_interaction_check
from app.tools.symptom_lookup import symptom_lookup
from app.tools.provider_search import provider_search
from app.tools.appointment_availability import appointment_availability
from app.tools.insurance_coverage import insurance_coverage_check
from app.tools.medication_lookup import medication_lookup
from app.tools.drug_recall import (
    manage_watchlist,
    check_drug_recalls,
    scan_watchlist_recalls,
)

__all__ = [
    "drug_interaction_check",
    "symptom_lookup",
    "provider_search",
    "appointment_availability",
    "insurance_coverage_check",
    "medication_lookup",
    "manage_watchlist",
    "check_drug_recalls",
    "scan_watchlist_recalls",
]
