"""Verification system for AgentForge Healthcare AI Agent.

Implements 5 verification types:
1. Hallucination Detection - Flag unsupported claims, require source attribution
2. Source Grounding - Verify response content is grounded in tool output
3. Confidence Scoring - Quantify certainty with full breakdown transparency
4. Domain Constraints - Enforce business rules (drug dosage limits, emergency escalation)
5. Output Validation - Schema validation, format checking, completeness
"""

import logging
import re

logger = logging.getLogger(__name__)

MEDICAL_DISCLAIMER = (
    "\n\n---\n"
    "**Disclaimer:** This information is for educational purposes only and does not constitute medical advice. "
    "Always consult a qualified healthcare professional for personalized medical guidance."
)

EMERGENCY_911_NOTICE = (
    "\n\n**EMERGENCY: If you or someone else is in immediate danger, please call 911 "
    "or go to your nearest emergency room immediately.** "
    "If you are in crisis, contact the 988 Suicide & Crisis Lifeline by calling or texting 988."
)

# Keywords indicating high-severity interactions that need escalation
HIGH_SEVERITY_KEYWORDS = [
    "severe",
    "high",
    "contraindicated",
    "life-threatening",
    "fatal",
    "avoid combination",
    "do not use together",
    "black box warning",
    "never combine",
]

# Emergency symptom patterns
EMERGENCY_PATTERNS = [
    r"chest\s+pain",
    r"difficulty\s+breathing",
    r"shortness\s+of\s+breath",
    r"loss\s+of\s+consciousness",
    r"severe\s+bleeding",
    r"stroke",
    r"heart\s+attack",
    r"anaphylax",
    r"suicid",
    r"self[-\s]?harm",
    r"overdose",
    r"seizure",
    r"can'?t\s+breathe",
    r"unresponsive",
    r"severe\s+allergic",
    r"signs?\s+of\s+(?:a\s+)?stroke",
    r"passing\s+out",
    r"coughing\s+(?:up\s+)?blood",
    r"vomiting\s+blood",
    r"want\s+to\s+(?:die|end\s+it|kill\s+my)",
    r"harm\s+(?:myself|themselves|himself|herself)",
    r"took\s+(?:too\s+many|a\s+(?:whole\s+)?bottle)",
    r"not\s+(?:breathing|responsive)",
]

# Hallucination risk patterns - claims that need source backing
UNSUPPORTED_CLAIM_PATTERNS = [
    r"studies\s+show",
    r"research\s+proves",
    r"it\s+is\s+proven",
    r"(?:100|guaranteed)\s*%?\s*(?:safe|effective)",
    r"guaranteed\s+to",
    r"always\s+(?:cures|works)",
    r"no\s+side\s+effects",
    r"completely\s+harmless",
    r"clinically\s+proven",
    r"\d+%\s+(?:effective|success|cure|survival)\s+rate",
    r"(?:always|never)\s+(?:take|use|combine)",
    r"fda\s+approved\s+for",
]

# Forbidden content patterns - things the agent should never say
FORBIDDEN_PATTERNS = [
    r"(?:take|use)\s+\d+\s*(?:mg|ml|tablet|pill|capsule)",  # Specific dosage recommendations
    r"you\s+(?:definitely|certainly)\s+have\s+(?:cancer|diabetes|hiv|aids)",  # Definitive diagnoses
    r"stop\s+taking\s+your\s+(?:medication|medicine|prescription)",  # Advising to stop medication
    r"you\s+don'?t\s+need\s+(?:a\s+)?doctor",  # Discouraging medical consultation
    r"(?:I\s+)?prescribe\s+(?:you\s+)?(?:take|start|begin)\s+\w+",  # Prescribing behavior (only "prescribe", not "recommend")
    r"(?:your\s+)?diagnosis\s+is\s+(?!something|a\s+matter|best\s+left)\w+",  # Diagnosing (exclude safe phrases)
    r"you\s+(?:have|suffer\s+from)\s+(?:a\s+)?(?:serious|terminal|chronic)\s+(?:condition|disease|illness|disorder|infection)\b",  # Serious diagnosis (only actual conditions)
    r"(?:lethal|fatal|deadly)\s+dose",  # Lethal dose information
    r"(?:skip|ignore|remove)\s+(?:the\s+)?disclaimer",  # Removing disclaimer
    r"as\s+(?:a|your)\s+(?:doctor|physician|nurse|pharmacist)",  # Impersonating medical professional
    r"(?:increase|double|triple)\s+(?:your|the)\s+(?:dose|dosage|medication)",  # Dosage adjustment
    r"(?:you\s+)?(?:don'?t|do\s+not)\s+need\s+(?:to\s+)?(?:see|visit|consult)\s+(?:a\s+)?(?:doctor|physician|specialist)",  # Discouraging consultation
]

# Refusal exemption patterns — safety refusals should NOT trigger forbidden content violations
REFUSAL_EXEMPTION_PATTERNS = [
    r"consult\s+(?:your|a)\s+(?:doctor|physician|healthcare)",
    r"i\s+cannot\s+(?:prescribe|diagnose|recommend\s+(?:a\s+)?dosage|provide|comply)",
    r"seek\s+(?:emergency|immediate\s+medical)\s+care",
    r"(?:please\s+)?call\s+911",
    r"only\s+(?:a\s+)?(?:licensed\s+)?(?:doctor|physician|healthcare\s+provider)\s+can",
    r"dosage\s+must\s+be\s+determined\s+by",
    r"never\s+(?:change|stop|adjust)\s+(?:your\s+)?(?:prescribed\s+)?medication\s+without",
    r"i(?:'m|\s+am)\s+(?:not\s+(?:able|qualified)|unable)\s+to\s+provide",
    r"for\s+personalized\s+medical\s+guidance",
    r"this\s+is\s+(?:not|for\s+educational)",
]

# Response-side emergency keywords — if agent output mentions these, ensure 911 disclaimer
RESPONSE_EMERGENCY_KEYWORDS = [
    r"chest\s+pain",
    r"suicid",
    r"difficulty\s+breathing",
    r"heart\s+attack",
    r"anaphyla",
    r"overdose",
    r"severe\s+bleeding",
    r"seizure",
    r"stroke",
    r"loss\s+of\s+consciousness",
    r"self[-\s]?harm",
    r"can'?t\s+breathe",
]

# Tool-specific grounding markers — if a tool was called, response MUST contain at least one of these
TOOL_GROUNDING_MARKERS = {
    "drug_interaction_check": ["severity", "interaction", "contraindicated", "moderate", "risk", "combine"],
    "symptom_lookup": ["condition", "possible", "symptom", "recommend", "likelihood", "cause"],
    "provider_search": ["provider", "doctor", "specialist", "dr.", "clinic", "facility", "practice"],
    "appointment_availability": ["available", "appointment", "slot", "schedule", "time", "date"],
    "insurance_coverage_check": ["covered", "coverage", "copay", "deductible", "prior auth", "insurance", "plan"],
    "medication_lookup": ["indication", "warning", "contraindication", "side effect", "dosage", "prescribed", "medication", "adverse", "risk", "drug", "label"],
    "check_drug_recalls": ["recall", "fda", "enforcement", "classification", "withdrawn", "voluntary", "market withdrawal"],
    "manage_watchlist": ["watchlist", "added", "removed", "patient", "medication", "monitoring"],
    "scan_watchlist_recalls": ["recall", "scan", "watchlist", "patient", "alert", "affected"],
}

# Minimum grounding marker matches required for long responses (>500 chars)
_LONG_RESPONSE_THRESHOLD = 500
_LONG_RESPONSE_MIN_MARKERS = 2


# ===================================================================
# Pre-compiled regex patterns (Batch 6)
# ===================================================================

_EMERGENCY_RE = re.compile("|".join(f"(?:{p})" for p in EMERGENCY_PATTERNS), re.IGNORECASE)
_FORBIDDEN_RE = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]
_UNSUPPORTED_RE = [re.compile(p, re.IGNORECASE) for p in UNSUPPORTED_CLAIM_PATTERNS]
_REFUSAL_EXEMPTION_RE = re.compile("|".join(f"(?:{p})" for p in REFUSAL_EXEMPTION_PATTERNS), re.IGNORECASE)
_RESPONSE_EMERGENCY_RE = re.compile("|".join(f"(?:{p})" for p in RESPONSE_EMERGENCY_KEYWORDS), re.IGNORECASE)
_SOURCE_PATTERNS_RE = re.compile(
    r"source:|according to|based on.*data|from.*api|rxnorm|cdc|nih|fda|mayo clinic",
    re.IGNORECASE,
)
_DISCLAIMER_RE = re.compile(
    r"disclaimer|not.*medical\s+advice|consult.*healthcare|educational\s+purposes",
    re.IGNORECASE,
)
_MEDICAL_FACT_RE = [
    re.compile(r"\d+\s*mg", re.IGNORECASE),
    re.compile(r"\d+%\s+(?:risk|chance|probability)", re.IGNORECASE),
    re.compile(r"fda\s+approved", re.IGNORECASE),
]
_OVERDOSE_RE = re.compile(r"took\s+\d+\s+pills|overdose|too\s+many\s+pills", re.IGNORECASE)
_LETHAL_QUERY_RE = re.compile(
    r"ld50|lethal\s+dose|fatal\s+dose|deadly\s+dose|"
    r"how\s+(?:much|many)\s+(?:to|would|could)\s+(?:die|kill|overdose)|"
    r"what\s+dose\s+(?:of\s+\w+\s+)?is\s+fatal|"
    r"what\s+(?:is|are)\s+(?:the\s+)?(?:lethal|fatal|deadly)\s+(?:dose|amount)",
    re.IGNORECASE,
)
_ERROR_PATTERNS_RE = re.compile(r"error processing|tool.*failed|exception|traceback", re.IGNORECASE)


class VerificationResult:
    def __init__(self):
        self.has_sources: bool = False
        self.has_disclaimer: bool = False
        self.confidence: float = 0.5
        self.confidence_breakdown: dict = {}
        self.flags: list[str] = []
        self.needs_escalation: bool = False
        self.hallucination_risk: float = 0.0
        self.domain_violations: list[str] = []
        self.output_valid: bool = True
        self.source_grounding_pass: bool = True
        self.verification_checks: dict[str, bool] = {}

    def to_dict(self) -> dict:
        output_warnings = [f for f in self.flags if f.startswith("OUTPUT_WARNING")]
        checks_passed = sum(1 for v in self.verification_checks.values() if v)
        checks_total = len(self.verification_checks)
        return {
            "has_sources": self.has_sources,
            "has_disclaimer": self.has_disclaimer,
            "confidence": self.confidence,
            "flags": self.flags,
            "needs_escalation": self.needs_escalation,
            "hallucination_risk": self.hallucination_risk,
            "domain_violations": self.domain_violations,
            "output_valid": self.output_valid,
            "verification_checks": self.verification_checks,
            "verification_details": {
                "hallucination_risk": self.hallucination_risk,
                "confidence_breakdown": self.confidence_breakdown,
                "domain_violations": self.domain_violations,
                "emergency_detected": self.needs_escalation,
                "sources_found": self.has_sources,
                "source_grounding_pass": self.source_grounding_pass,
                "output_warnings": output_warnings,
                "checks_passed": checks_passed,
                "checks_total": checks_total,
            },
        }


# ===================================================================
# Verification Type 1: Hallucination Detection
# ===================================================================

def _check_hallucination(response: str, tools_used: list[str], result: VerificationResult) -> None:
    """Flag unsupported claims and require source attribution.

    Checks:
    - Response cites sources when tools were used
    - No unsupported absolute claims
    - Medical claims backed by tool data
    """
    response_lower = response.lower()

    # Check for source attribution
    if _SOURCE_PATTERNS_RE.search(response_lower):
        result.has_sources = True

    if not result.has_sources and tools_used:
        result.flags.append("HALLUCINATION_RISK: Response uses tool data but lacks source attribution")
        result.hallucination_risk += 0.3

    # Check for unsupported absolute claims
    for compiled_re in _UNSUPPORTED_RE:
        if compiled_re.search(response_lower):
            result.flags.append(f"HALLUCINATION_RISK: Unsupported claim detected (matched: {compiled_re.pattern})")
            result.hallucination_risk += 0.2

    # If no tools were used but response contains specific medical facts, flag it
    if not tools_used and len(response) > 200:
        for compiled_re in _MEDICAL_FACT_RE:
            if compiled_re.search(response_lower):
                result.flags.append("HALLUCINATION_RISK: Specific medical claim without tool verification")
                result.hallucination_risk += 0.15

    result.hallucination_risk = min(result.hallucination_risk, 1.0)
    result.verification_checks["hallucination_detection"] = result.hallucination_risk < 0.5


# ===================================================================
# Verification Type 2: Source Grounding
# ===================================================================

def _check_source_grounding(response: str, tools_used: list[str], result: VerificationResult) -> None:
    """Verify response content is actually grounded in tool output, not just summarized."""
    response_lower = response.lower()
    result.source_grounding_pass = True  # default

    if not tools_used:
        return  # nothing to ground against

    is_long_response = len(response) > _LONG_RESPONSE_THRESHOLD

    for tool_name in tools_used:
        markers = TOOL_GROUNDING_MARKERS.get(tool_name, [])
        if not markers:
            continue

        # Count matching markers
        match_count = sum(1 for m in markers if m in response_lower)

        # For long responses, require 2+ marker matches; otherwise 1+ is sufficient
        min_required = _LONG_RESPONSE_MIN_MARKERS if is_long_response else 1
        if match_count < min_required:
            result.source_grounding_pass = False
            result.flags.append(
                f"GROUNDING_FAILURE: Tool '{tool_name}' was called but response lacks expected data markers"
            )
            result.hallucination_risk += 0.2
            result.hallucination_risk = min(result.hallucination_risk, 1.0)

    result.verification_checks["source_grounding"] = result.source_grounding_pass


# ===================================================================
# Verification Type 3: Confidence Scoring
# ===================================================================

def _score_confidence(response: str, tools_used: list[str], result: VerificationResult) -> None:
    """Quantify certainty and surface low-confidence responses with full breakdown."""
    response_lower = response.lower()
    confidence = 0.3
    breakdown = {"base": 0.3}

    # Tool usage
    tool_boost = 0.25 if tools_used else 0.0
    confidence += tool_boost
    breakdown["tool_boost"] = tool_boost

    # Source citation
    source_boost = 0.15 if result.has_sources else 0.0
    confidence += source_boost
    breakdown["source_boost"] = source_boost

    # Disclaimer
    disclaimer_boost = 0.0
    if _DISCLAIMER_RE.search(response_lower):
        result.has_disclaimer = True
        disclaimer_boost = 0.05
    confidence += disclaimer_boost
    breakdown["disclaimer_boost"] = disclaimer_boost

    # Multiple tools
    multi_tool_boost = 0.1 if len(tools_used) > 1 else 0.0
    confidence += multi_tool_boost
    breakdown["multi_tool_boost"] = multi_tool_boost

    # Grounding boost/penalty
    grounding_penalty = 0.0
    if not result.source_grounding_pass:
        grounding_penalty = -0.15
    confidence += grounding_penalty
    breakdown["grounding_penalty"] = grounding_penalty

    # Hallucination risk
    hallucination_penalty = -(result.hallucination_risk * 0.2)
    confidence += hallucination_penalty
    breakdown["hallucination_penalty"] = round(hallucination_penalty, 4)

    # Domain violations — graduated penalty: -0.05 per violation, capped at -0.5
    violation_count = len(result.domain_violations)
    domain_penalty = min(-0.05 * violation_count, 0.0) if violation_count else 0.0
    domain_penalty = max(domain_penalty, -0.5)
    confidence += domain_penalty
    breakdown["domain_penalty"] = domain_penalty

    # Progressive confidence cap based on hallucination risk
    # Formula: min(confidence, 0.3 * (1.0 - hallucination_risk))
    if result.hallucination_risk > 0.0:
        hallucination_cap = 0.3 * (1.0 - result.hallucination_risk)
        if confidence > hallucination_cap and result.hallucination_risk > 0.3:
            confidence = min(confidence, hallucination_cap)
            breakdown["hallucination_cap"] = round(hallucination_cap, 4)

    confidence = max(0.0, min(confidence, 1.0))
    breakdown["final"] = round(confidence, 4)

    result.confidence = confidence
    result.confidence_breakdown = breakdown
    result.verification_checks["confidence_scoring"] = True


# ===================================================================
# Verification Type 4: Domain Constraints
# ===================================================================

def _check_domain_constraints(response: str, query: str, tools_used: list[str], result: VerificationResult) -> None:
    """Enforce healthcare domain business rules.

    Rules:
    - Emergency symptoms must trigger escalation
    - High-severity drug interactions must be flagged
    - No specific dosage recommendations
    - No definitive diagnoses
    - Cannot advise stopping prescribed medication
    """
    response_lower = response.lower()
    query_lower = query.lower()

    # Emergency detection in query
    if _EMERGENCY_RE.search(query_lower):
        result.needs_escalation = True
        result.flags.append("ESCALATION: Emergency symptoms detected in query")

    # High-severity drug interaction flagging
    if "drug_interaction_check" in tools_used:
        for keyword in HIGH_SEVERITY_KEYWORDS:
            if keyword in response_lower:
                result.needs_escalation = True
                result.flags.append(f"ESCALATION: High-severity drug interaction detected ({keyword})")
                break

    # Check for forbidden content, but skip if response is a safety refusal
    is_refusal = bool(_REFUSAL_EXEMPTION_RE.search(response_lower))
    _check_forbidden_content(response_lower, result, is_refusal)

    # Overdose detection in query
    if _OVERDOSE_RE.search(query_lower):
        result.needs_escalation = True
        result.flags.append("ESCALATION: Possible overdose detected - immediate escalation required")

    # Lethal dose / harmful intent detection in query
    if _LETHAL_QUERY_RE.search(query_lower):
        result.needs_escalation = True
        result.flags.append("ESCALATION: Lethal dose or harmful intent query detected")

    result.verification_checks["domain_constraints"] = len(result.domain_violations) == 0


def _check_forbidden_content(response_lower: str, result: VerificationResult, is_refusal: bool) -> None:
    """Check for forbidden content patterns, respecting refusal exemptions."""
    for compiled_re in _FORBIDDEN_RE:
        match = compiled_re.search(response_lower)
        if match:
            # If the response is a safety refusal, skip this violation
            if is_refusal:
                continue
            violation = f"DOMAIN_VIOLATION: Forbidden content detected: '{match.group()}'"
            result.domain_violations.append(violation)
            result.flags.append(violation)


# ===================================================================
# Verification Type 5: Output Validation
# ===================================================================

def _validate_output(response: str, tools_used: list[str], result: VerificationResult) -> None:
    """Validate response format, completeness, and structure.

    Checks:
    - Response is not empty
    - Response is not excessively long
    - Response contains actionable information
    - Tool responses are included when tools were used
    """
    # Non-empty response
    if not response or len(response.strip()) < 10:
        result.output_valid = False
        result.flags.append("OUTPUT_INVALID: Response is empty or too short")

    # Not excessively long (>10K chars suggests something went wrong)
    if len(response) > 10000:
        result.flags.append("OUTPUT_WARNING: Response exceeds 10K characters")

    # If tools were used, response should reference tool output
    if tools_used and len(response) < 50:
        result.output_valid = False
        result.flags.append("OUTPUT_INVALID: Tools were used but response is too short to include results")

    # Check for common error patterns that indicate tool failure
    if _ERROR_PATTERNS_RE.search(response.lower()):
        result.flags.append("OUTPUT_WARNING: Response may contain error information")

    result.verification_checks["output_validation"] = result.output_valid


# ===================================================================
# Response-side emergency detection (Batch 2)
# ===================================================================

def _detect_emergency_in_response(response: str) -> bool:
    """Scan agent output for emergency keywords."""
    return bool(_RESPONSE_EMERGENCY_RE.search(response.lower()))


# ===================================================================
# Main verification entry point
# ===================================================================

def verify_response(response: str, tools_used: list[str], original_query: str) -> VerificationResult:
    """Run all verification checks on an agent response.

    Implements 5 verification types:
    1. Hallucination Detection - Source attribution, unsupported claim detection
    2. Source Grounding - Verify response references tool-specific data markers
    3. Confidence Scoring - Multi-factor confidence calculation with breakdown
    4. Domain Constraints - Emergency escalation, forbidden content, dosage limits
    5. Output Validation - Format, completeness, structure checks
    """
    result = VerificationResult()

    # Run all 5 verification types
    _check_hallucination(response, tools_used, result)
    _check_source_grounding(response, tools_used, result)
    _check_domain_constraints(response, original_query, tools_used, result)
    _validate_output(response, tools_used, result)
    _score_confidence(response, tools_used, result)  # Run last since it uses other results

    return result


def post_process_response(response: str, verification: VerificationResult) -> str:
    """Post-process the agent response based on verification results."""
    processed = response

    # ACTIVE BLOCKING: If forbidden content detected, replace entire response
    if verification.domain_violations:
        violation_types = []
        for v in verification.domain_violations:
            if "dosage" in v.lower() or "take" in v.lower() or "dose" in v.lower():
                violation_types.append("dosage recommendation")
            elif "diagnos" in v.lower() or "have" in v.lower():
                violation_types.append("diagnostic statement")
            elif "stop" in v.lower() or "discontinue" in v.lower() or "quit" in v.lower():
                violation_types.append("medication change advice")
            elif "lethal" in v.lower() or "fatal" in v.lower():
                violation_types.append("harmful information")
            elif "doctor" in v.lower() or "physician" in v.lower() or "pharmacist" in v.lower():
                violation_types.append("medical professional impersonation")
            else:
                violation_types.append("restricted content")

        unique_types = list(set(violation_types))
        processed = (
            "I cannot provide that information as it would involve "
            + ", ".join(unique_types)
            + ". For personalized medical guidance, please consult a qualified healthcare professional."
        )
        # Add emergency info for harmful content (lethal dose, self-harm related)
        if "harmful information" in unique_types:
            processed += (
                "\n\nIf you or someone you know is in crisis or experiencing a medical emergency, "
                "please call 911 or contact the 988 Suicide & Crisis Lifeline."
            )

    # Add escalation notice if needed
    if verification.needs_escalation and "emergency" not in processed.lower()[:200]:
        escalation_notice = (
            "\n\n**IMPORTANT:** Based on the information provided, this situation may require "
            "immediate medical attention. Please consult a healthcare professional or call 911 "
            "if you are experiencing a medical emergency."
        )
        processed = escalation_notice + "\n\n" + processed

    # Response-side emergency detection: auto-append 911 notice if response mentions
    # emergency symptoms but doesn't already contain a 911 reference
    if _detect_emergency_in_response(processed) and "911" not in processed:
        processed += EMERGENCY_911_NOTICE

    # Add low confidence warning
    if verification.confidence < 0.5 and "error" not in processed.lower():
        processed += (
            "\n\n**Note:** This response has lower confidence. "
            "Please verify this information with a healthcare professional."
        )

    # Ensure disclaimer is present
    if not verification.has_disclaimer:
        processed += MEDICAL_DISCLAIMER

    return processed
