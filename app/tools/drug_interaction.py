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
    frozenset(["metformin", "ibuprofen"]): {
        "severity": "Moderate",
        "description": (
            "NSAIDs like ibuprofen can impair kidney function and reduce metformin clearance, "
            "potentially increasing the risk of lactic acidosis. This risk is higher in patients "
            "with pre-existing renal impairment."
        ),
        "source": "NIH DailyMed, American Diabetes Association",
        "clinical_action": "Use with caution. Monitor kidney function. Consider acetaminophen as alternative.",
    },
    frozenset(["atorvastatin", "amiodarone"]): {
        "severity": "High",
        "description": (
            "Amiodarone inhibits CYP3A4 and increases atorvastatin levels, raising the risk of "
            "myopathy and rhabdomyolysis. Atorvastatin dose should not exceed 40mg/day with amiodarone."
        ),
        "source": "FDA Drug Safety Communication",
        "clinical_action": "Limit atorvastatin to 40mg/day. Monitor for muscle pain, tenderness, or weakness.",
    },
    frozenset(["warfarin", "omeprazole"]): {
        "severity": "Moderate",
        "description": (
            "Omeprazole may increase warfarin levels by inhibiting CYP2C19, leading to increased "
            "INR and bleeding risk. The interaction is generally mild but clinically relevant."
        ),
        "source": "FDA Drug Safety Communication, NIH DailyMed",
        "clinical_action": "Monitor INR closely when starting or stopping omeprazole. Consider pantoprazole as alternative.",
    },
    frozenset(["lisinopril", "ibuprofen"]): {
        "severity": "Moderate",
        "description": (
            "NSAIDs like ibuprofen reduce the antihypertensive effect of ACE inhibitors and "
            "can impair kidney function, especially in patients with existing renal issues or dehydration."
        ),
        "source": "FDA Drug Safety Communication, American Heart Association",
        "clinical_action": "Avoid long-term NSAID use with ACE inhibitors. Monitor blood pressure and kidney function.",
    },
    frozenset(["metformin", "atorvastatin"]): {
        "severity": "Low",
        "description": (
            "Metformin and atorvastatin are commonly prescribed together for patients with diabetes "
            "and hyperlipidemia. No significant pharmacokinetic interaction. Both are generally well tolerated."
        ),
        "source": "NIH DailyMed, American Diabetes Association",
        "clinical_action": "Generally safe combination. Monitor blood glucose and lipid levels as usual.",
    },
    frozenset(["amlodipine", "simvastatin"]): {
        "severity": "High",
        "description": (
            "Amlodipine increases simvastatin exposure by inhibiting CYP3A4. The FDA recommends "
            "limiting simvastatin to 20mg/day when co-administered with amlodipine due to risk "
            "of rhabdomyolysis."
        ),
        "source": "FDA Drug Safety Communication",
        "clinical_action": "Do not exceed simvastatin 20mg/day. Consider switching to pravastatin or rosuvastatin.",
    },
    frozenset(["omeprazole", "clopidogrel"]): {
        "severity": "High",
        "description": (
            "Omeprazole strongly inhibits CYP2C19, reducing the conversion of clopidogrel to its "
            "active metabolite by up to 45%. This significantly reduces the antiplatelet effect and "
            "increases the risk of cardiovascular events."
        ),
        "source": "FDA Black Box Warning, ACC/AHA Guidelines",
        "clinical_action": "AVOID combination. Use pantoprazole or famotidine instead if acid suppression needed.",
    },
    frozenset(["sertraline", "tramadol"]): {
        "severity": "High",
        "description": (
            "Both sertraline and tramadol increase serotonin levels. The combination increases "
            "the risk of serotonin syndrome (agitation, hyperthermia, tachycardia, muscle rigidity) "
            "and may lower the seizure threshold."
        ),
        "source": "FDA Drug Safety Communication, NIH DailyMed",
        "clinical_action": "Avoid combination if possible. Use alternative analgesics. Monitor for serotonin syndrome.",
    },
    frozenset(["lisinopril", "spironolactone"]): {
        "severity": "High",
        "description": (
            "Both ACE inhibitors and spironolactone increase potassium levels. Combined use "
            "significantly raises the risk of life-threatening hyperkalemia, especially in "
            "patients with renal impairment."
        ),
        "source": "FDA Drug Safety Communication, ACC/AHA Heart Failure Guidelines",
        "clinical_action": "If combination is necessary, monitor serum potassium within 1 week and regularly thereafter.",
    },
    frozenset(["warfarin", "amoxicillin"]): {
        "severity": "Moderate",
        "description": (
            "Antibiotics including amoxicillin can disrupt gut flora that produce vitamin K, "
            "potentially increasing INR and bleeding risk in patients on warfarin."
        ),
        "source": "NIH DailyMed, American College of Cardiology",
        "clinical_action": "Monitor INR within 3-5 days of starting antibiotic. Temporary dose adjustment may be needed.",
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


async def _check_rxnorm_interactions(client: httpx.AsyncClient, rxcuis: list[str]) -> list[dict]:
    """Query the RxNorm interaction API for interactions between resolved RxCUIs."""
    if len(rxcuis) < 2:
        return []
    interactions = []
    try:
        rxcui_str = "+".join(rxcuis)
        resp = await client.get(
            f"{RXNAV_BASE}/interaction/list.json",
            params={"rxcuis": rxcui_str},
        )
        if resp.status_code == 200:
            data = resp.json()
            interaction_groups = data.get("fullInteractionTypeGroup", [])
            for group in interaction_groups:
                source = group.get("sourceName", "RxNorm")
                for itype in group.get("fullInteractionType", []):
                    for pair in itype.get("interactionPair", []):
                        desc = pair.get("description", "")
                        severity = pair.get("severity", "N/A")
                        if severity == "N/A":
                            severity = "Moderate"
                        concepts = pair.get("interactionConcept", [])
                        drug_names = [
                            c.get("minConceptItem", {}).get("name", "Unknown")
                            for c in concepts
                        ]
                        interactions.append({
                            "drugs": drug_names,
                            "severity": severity,
                            "description": desc,
                            "source": f"RxNorm / {source}",
                            "clinical_action": "Consult your pharmacist or healthcare provider for guidance.",
                        })
    except Exception as e:
        logger.warning("RxNorm interaction API error: %s", e)
    return interactions


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

    # Track data provenance for transparent source attribution
    used_local_db = False
    used_rxnorm_api = False

    # Check local database first (most reliable for known pairs)
    interactions = _check_local_interactions(drug_names)
    if interactions:
        used_local_db = True

    # Validate drug names via RxNorm API and look up interactions if none found locally
    validated_drugs = []
    unvalidated_drugs = []
    resolved_rxcuis = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name in drug_names:
                rxcui = await _resolve_rxcui(client, name.strip())
                if rxcui:
                    validated_drugs.append(name)
                    resolved_rxcuis.append(rxcui)
                    used_rxnorm_api = True
                else:
                    unvalidated_drugs.append(name)

            # If no local interactions found, try RxNorm interaction API
            if not interactions and len(resolved_rxcuis) >= 2:
                rxnorm_interactions = await _check_rxnorm_interactions(client, resolved_rxcuis)
                if rxnorm_interactions:
                    interactions.extend(rxnorm_interactions)
                    used_rxnorm_api = True
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
        source_parts = []
        if used_rxnorm_api:
            source_parts.append("RxNorm API (Live)")
        source_parts.append("AgentForge Drug Interaction Database (curated from FDA/NIH public data)")
        result_lines.append(f"Source: {', '.join(source_parts)}")
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
    source_parts = []
    if used_rxnorm_api:
        source_parts.append("RxNorm API (Live — https://rxnav.nlm.nih.gov/)")
    if used_local_db:
        source_parts.append("AgentForge Drug Interaction Database (curated from FDA/NIH public data)")
    if not source_parts:
        source_parts.append("RxNorm API")
    lines.append(f"Source: {', '.join(source_parts)}")
    lines.append(
        "DISCLAIMER: This information is for educational purposes only. "
        "Always consult a pharmacist or healthcare professional before making medication changes."
    )
    return "\n".join(lines)
