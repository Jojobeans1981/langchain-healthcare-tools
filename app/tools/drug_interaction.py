import logging

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"

# Local drug interaction database - curated from FDA/NIH public data
# Used as primary source with RxNorm for drug name validation
KNOWN_INTERACTIONS = {
    frozenset(["warfarin", "aspirin"]): {
        "severity": "High",
        "description": (
            "Concurrent use of warfarin and aspirin increases the risk of bleeding significantly. "
            "Aspirin inhibits platelet aggregation while warfarin inhibits clotting factors, "
            "creating a compounded anticoagulant effect. Monitor INR closely if combination is necessary."
        ),
        "source": "FDA Drug Safety Communication, NIH DailyMed",
        "clinical_action": "Avoid combination unless specifically directed by physician. Monitor for signs of bleeding.",
    },
    frozenset(["warfarin", "ibuprofen"]): {
        "severity": "High",
        "description": (
            "NSAIDs like ibuprofen increase the anticoagulant effect of warfarin and increase bleeding risk. "
            "Ibuprofen also irritates the gastric mucosa, further increasing GI bleeding risk."
        ),
        "source": "FDA Drug Safety Communication, NIH DailyMed",
        "clinical_action": "Avoid combination. Use acetaminophen for pain relief instead if on warfarin.",
    },
    frozenset(["warfarin", "acetaminophen"]): {
        "severity": "Moderate",
        "description": (
            "Regular use of acetaminophen (>2g/day for several days) may enhance the anticoagulant effect "
            "of warfarin, increasing INR. Occasional use at recommended doses is generally considered safe."
        ),
        "source": "NIH DailyMed, American Heart Association",
        "clinical_action": "Monitor INR if using acetaminophen regularly. Limit to less than 2g/day.",
    },
    frozenset(["ibuprofen", "aspirin"]): {
        "severity": "Moderate",
        "description": (
            "Ibuprofen may interfere with the antiplatelet effect of low-dose aspirin. "
            "If taken together, ibuprofen should be taken at least 30 minutes after or 8 hours before aspirin."
        ),
        "source": "FDA Drug Safety Communication",
        "clinical_action": "Separate administration times. Consult physician about timing.",
    },
    frozenset(["ibuprofen", "acetaminophen"]): {
        "severity": "Low",
        "description": (
            "Ibuprofen and acetaminophen can generally be taken together or alternated safely "
            "at recommended doses. They work by different mechanisms and can provide complementary pain relief."
        ),
        "source": "American Academy of Pediatrics, FDA",
        "clinical_action": "Generally safe at recommended doses. Do not exceed maximum daily dose of either drug.",
    },
    frozenset(["metformin", "lisinopril"]): {
        "severity": "Low",
        "description": (
            "Metformin and lisinopril are commonly prescribed together for patients with diabetes and "
            "hypertension. ACE inhibitors like lisinopril may slightly improve insulin sensitivity. "
            "No clinically significant adverse interaction."
        ),
        "source": "NIH DailyMed, American Diabetes Association",
        "clinical_action": "Generally safe combination. Monitor kidney function regularly.",
    },
    frozenset(["metformin", "alcohol"]): {
        "severity": "High",
        "description": (
            "Alcohol consumption while taking metformin increases the risk of lactic acidosis, "
            "a rare but potentially fatal condition. Alcohol also affects blood sugar levels."
        ),
        "source": "FDA Black Box Warning, NIH DailyMed",
        "clinical_action": "Limit alcohol intake. Avoid binge drinking. Seek emergency care if symptoms of lactic acidosis.",
    },
    frozenset(["simvastatin", "amiodarone"]): {
        "severity": "High",
        "description": (
            "Amiodarone significantly increases simvastatin levels, increasing the risk of rhabdomyolysis "
            "(severe muscle breakdown). Simvastatin dose should not exceed 20mg/day with amiodarone."
        ),
        "source": "FDA Drug Safety Communication",
        "clinical_action": "Limit simvastatin to 20mg/day or switch to alternative statin.",
    },
    frozenset(["ssri", "maoi"]): {
        "severity": "Contraindicated",
        "description": (
            "Combining SSRIs (e.g., fluoxetine, sertraline) with MAOIs can cause serotonin syndrome, "
            "a potentially life-threatening condition with symptoms including agitation, hyperthermia, "
            "and neuromuscular changes."
        ),
        "source": "FDA Black Box Warning",
        "clinical_action": "NEVER combine. At least 14-day washout period required between medications.",
    },
    frozenset(["fluoxetine", "tramadol"]): {
        "severity": "High",
        "description": (
            "Combining fluoxetine (an SSRI) with tramadol increases the risk of serotonin syndrome "
            "and may lower seizure threshold. Both drugs affect serotonin reuptake."
        ),
        "source": "FDA Drug Safety Communication, NIH DailyMed",
        "clinical_action": "Use alternative pain management. Monitor for serotonin syndrome symptoms.",
    },
    frozenset(["lisinopril", "potassium"]): {
        "severity": "High",
        "description": (
            "ACE inhibitors like lisinopril increase potassium retention. Adding potassium supplements "
            "can lead to dangerous hyperkalemia (high potassium), which can cause cardiac arrhythmias."
        ),
        "source": "FDA Drug Safety Communication, NIH DailyMed",
        "clinical_action": "Avoid potassium supplements unless directed by physician. Monitor serum potassium.",
    },
}


class DrugInteractionInput(BaseModel):
    drug_names: list[str] = Field(
        description="List of two or more drug names to check for interactions (e.g. ['warfarin', 'aspirin'])"
    )


def _normalize_drug_name(name: str) -> str:
    """Normalize drug name for matching."""
    return name.strip().lower()


def _check_local_interactions(drug_names: list[str]) -> list[dict]:
    """Check the local interaction database for known interactions."""
    normalized = [_normalize_drug_name(n) for n in drug_names]
    interactions = []

    # Check all pairs
    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            pair = frozenset([normalized[i], normalized[j]])
            if pair in KNOWN_INTERACTIONS:
                interaction = KNOWN_INTERACTIONS[pair].copy()
                interaction["drugs"] = [drug_names[i], drug_names[j]]
                interactions.append(interaction)

    return interactions


async def _resolve_rxcui(client: httpx.AsyncClient, drug_name: str) -> str | None:
    """Resolve a drug name to its RxNorm Concept Unique Identifier (RxCUI)."""
    try:
        resp = await client.get(f"{RXNAV_BASE}/rxcui.json", params={"name": drug_name, "search": 2})
        if resp.status_code == 200:
            data = resp.json()
            id_group = data.get("idGroup", {})
            rxnorm_ids = id_group.get("rxnormId")
            if rxnorm_ids:
                return rxnorm_ids[0]
        # Try approximate match
        resp = await client.get(f"{RXNAV_BASE}/approximateTerm.json", params={"term": drug_name, "maxEntries": 1})
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("approximateGroup", {}).get("candidate", [])
            if candidates:
                return candidates[0].get("rxcui")
    except Exception as e:
        logger.warning("RxNorm API error for %s: %s", drug_name, e)
    return None


@tool(args_schema=DrugInteractionInput)
async def drug_interaction_check(drug_names: list[str]) -> str:
    """Check for drug-drug interactions between two or more medications.

    Uses a curated drug interaction database validated against FDA and NIH sources,
    with RxNorm for drug name verification. Provides severity levels, clinical
    descriptions, and recommended actions.
    Always use this tool when a patient asks about combining medications.
    """
    if len(drug_names) < 2:
        return "Error: Please provide at least two drug names to check for interactions."

    drug_list = ", ".join(drug_names)

    # Check local database first (most reliable for known pairs)
    interactions = _check_local_interactions(drug_names)

    # Validate drug names via RxNorm API
    validated_drugs = []
    unvalidated_drugs = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name in drug_names:
                rxcui = await _resolve_rxcui(client, name.strip())
                if rxcui:
                    validated_drugs.append(name)
                else:
                    unvalidated_drugs.append(name)
    except Exception as e:
        logger.warning("RxNorm validation unavailable: %s", e)
        # If RxNorm is down, treat all as validated for local lookup
        validated_drugs = drug_names

    # Format response
    if not interactions:
        result_lines = [f"Drug Interaction Check: {drug_list}", ""]

        if unvalidated_drugs:
            result_lines.append(
                f"WARNING: Could not verify the following drug names in RxNorm: {', '.join(unvalidated_drugs)}. "
                "Please check spelling."
            )
            result_lines.append("")

        result_lines.append(
            f"No known interactions found between: {drug_list}."
        )
        result_lines.append("")
        result_lines.append(
            "Note: This database covers common drug interactions but may not include all possible interactions. "
            "The absence of a listed interaction does not guarantee safety."
        )
        result_lines.append("")
        result_lines.append("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]")
        result_lines.append("Source: FDA Drug Safety Database, NIH DailyMed, RxNorm")
        result_lines.append(
            "DISCLAIMER: This information is for educational purposes only. "
            "Always consult a pharmacist or healthcare professional before combining medications."
        )
        return "\n".join(result_lines)

    lines = [
        f"Drug Interaction Results for: {drug_list}",
        f"Found {len(interactions)} interaction(s):",
        "",
    ]

    for i, interaction in enumerate(interactions, 1):
        drugs = interaction.get("drugs", [])
        lines.append(f"Interaction {i}: {' <-> '.join(drugs)}")
        lines.append(f"  Severity: {interaction['severity']}")
        lines.append(f"  Description: {interaction['description']}")
        lines.append(f"  Recommended Action: {interaction.get('clinical_action', 'Consult healthcare provider')}")
        lines.append(f"  Source: {interaction['source']}")
        lines.append("")

    if unvalidated_drugs:
        lines.append(f"Note: Could not verify in RxNorm: {', '.join(unvalidated_drugs)}")
        lines.append("")

    lines.append("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]")
    lines.append("Source: FDA Drug Safety Database, NIH DailyMed, RxNorm (https://rxnav.nlm.nih.gov/)")
    lines.append(
        "DISCLAIMER: This information is for educational purposes only. "
        "Always consult a pharmacist or healthcare professional before making medication changes."
    )
    return "\n".join(lines)
