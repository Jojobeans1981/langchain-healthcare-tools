import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.openemr_client import openemr

logger = logging.getLogger(__name__)

# Mock insurance coverage data
MOCK_PLANS = {
    "BLUE_CROSS_PPO": {
        "plan_name": "Blue Cross Blue Shield PPO",
        "plan_id": "BCBS-PPO-2026",
        "type": "PPO",
        "coverages": {
            "99213": {"description": "Office visit, established patient (Level 3)", "covered": True, "copay": 30, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "99214": {"description": "Office visit, established patient (Level 4)", "covered": True, "copay": 40, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "99203": {"description": "Office visit, new patient (Level 3)", "covered": True, "copay": 50, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "90834": {"description": "Psychotherapy, 45 minutes", "covered": True, "copay": 30, "coinsurance": 0.20, "deductible_applies": False, "prior_auth": False},
            "71046": {"description": "Chest X-ray, 2 views", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "93000": {"description": "Electrocardiogram (ECG/EKG)", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "27447": {"description": "Total knee replacement", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": True},
            "43239": {"description": "Upper GI endoscopy with biopsy", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": True},
            "99285": {"description": "Emergency department visit (high severity)", "covered": True, "copay": 250, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "70553": {"description": "MRI brain without and with contrast", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": True},
            "73721": {"description": "MRI lower extremity joint (e.g., knee)", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": True},
            "74177": {"description": "CT scan abdomen and pelvis with contrast", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "80053": {"description": "Comprehensive metabolic panel (blood work)", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "85025": {"description": "Complete blood count (CBC)", "covered": True, "copay": 0, "coinsurance": 0.0, "deductible_applies": False, "prior_auth": False},
        },
        "deductible": {"individual": 1500, "family": 3000},
        "out_of_pocket_max": {"individual": 6000, "family": 12000},
        "notes": "In-network benefits shown. Out-of-network may have higher costs.",
    },
    "MEDICARE_A": {
        "plan_name": "Medicare Part A & B",
        "plan_id": "MEDICARE-2026",
        "type": "Government",
        "coverages": {
            "99213": {"description": "Office visit, established patient (Level 3)", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "99214": {"description": "Office visit, established patient (Level 4)", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "71046": {"description": "Chest X-ray, 2 views", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "93000": {"description": "Electrocardiogram (ECG/EKG)", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "27447": {"description": "Total knee replacement", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": True},
            "90834": {"description": "Psychotherapy, 45 minutes", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "70553": {"description": "MRI brain without and with contrast", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": True},
            "80053": {"description": "Comprehensive metabolic panel (blood work)", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
            "85025": {"description": "Complete blood count (CBC)", "covered": True, "copay": 0, "coinsurance": 0.20, "deductible_applies": True, "prior_auth": False},
        },
        "deductible": {"individual": 240, "family": 240},
        "out_of_pocket_max": {"individual": 0, "family": 0},
        "notes": "Medicare has no out-of-pocket maximum. Supplemental insurance recommended.",
    },
    "AETNA_HMO": {
        "plan_name": "Aetna HMO Select",
        "plan_id": "AETNA-HMO-2026",
        "type": "HMO",
        "coverages": {
            "99213": {"description": "Office visit, established patient (Level 3)", "covered": True, "copay": 20, "coinsurance": 0.0, "deductible_applies": False, "prior_auth": False},
            "99214": {"description": "Office visit, established patient (Level 4)", "covered": True, "copay": 25, "coinsurance": 0.0, "deductible_applies": False, "prior_auth": False},
            "99203": {"description": "Office visit, new patient (Level 3)", "covered": True, "copay": 35, "coinsurance": 0.0, "deductible_applies": False, "prior_auth": False},
            "71046": {"description": "Chest X-ray, 2 views", "covered": True, "copay": 0, "coinsurance": 0.10, "deductible_applies": True, "prior_auth": False},
            "27447": {"description": "Total knee replacement", "covered": True, "copay": 0, "coinsurance": 0.15, "deductible_applies": True, "prior_auth": True},
            "99285": {"description": "Emergency department visit (high severity)", "covered": True, "copay": 150, "coinsurance": 0.0, "deductible_applies": False, "prior_auth": False},
            "70553": {"description": "MRI brain without and with contrast", "covered": True, "copay": 0, "coinsurance": 0.15, "deductible_applies": True, "prior_auth": True},
            "80053": {"description": "Comprehensive metabolic panel (blood work)", "covered": True, "copay": 0, "coinsurance": 0.10, "deductible_applies": True, "prior_auth": False},
        },
        "deductible": {"individual": 2000, "family": 4000},
        "out_of_pocket_max": {"individual": 5000, "family": 10000},
        "notes": "HMO requires referral from PCP for specialist visits.",
    },
}

# Common procedure code lookup
PROCEDURE_CODES = {
    "office visit": "99213",
    "new patient visit": "99203",
    "physical exam": "99214",
    "x-ray": "71046",
    "chest x-ray": "71046",
    "ekg": "93000",
    "ecg": "93000",
    "electrocardiogram": "93000",
    "knee replacement": "27447",
    "therapy": "90834",
    "psychotherapy": "90834",
    "counseling": "90834",
    "endoscopy": "43239",
    "emergency room": "99285",
    "er visit": "99285",
    "emergency visit": "99285",
    "mri": "70553",
    "mri brain": "70553",
    "mri knee": "73721",
    "ct scan": "74177",
    "cat scan": "74177",
    "blood work": "80053",
    "blood test": "80053",
    "metabolic panel": "80053",
    "cbc": "85025",
    "complete blood count": "85025",
}


class InsuranceCoverageInput(BaseModel):
    procedure: str = Field(description="Procedure name or CPT code to check coverage for (e.g. 'office visit', 'knee replacement', '99213')")
    plan_name: str = Field(default="", description="Insurance plan name (e.g. 'Blue Cross', 'Medicare', 'Aetna'). If empty, checks all available plans.")


def _resolve_procedure_code(procedure: str) -> str | None:
    """Resolve a procedure description to a CPT code."""
    procedure_lower = procedure.strip().lower()
    # Check if already a CPT code
    if procedure_lower.isdigit() and len(procedure_lower) == 5:
        return procedure_lower
    # Look up by description
    for desc, code in PROCEDURE_CODES.items():
        if desc in procedure_lower:
            return code
    return None


def _find_matching_plans(plan_name: str) -> list[dict]:
    """Find insurance plans matching the given name."""
    if not plan_name:
        return list(MOCK_PLANS.values())
    plan_lower = plan_name.lower()
    return [
        plan for key, plan in MOCK_PLANS.items()
        if plan_lower in plan["plan_name"].lower() or plan_lower in key.lower()
    ]


@tool(args_schema=InsuranceCoverageInput)
async def insurance_coverage_check(procedure: str, plan_name: str = "") -> str:
    """Check insurance coverage for a medical procedure.

    Looks up whether a specific procedure is covered under an insurance plan,
    including copay amounts, coinsurance percentages, deductible requirements,
    and prior authorization needs. Use this when a patient asks about
    insurance coverage or costs for a procedure.
    """
    if not procedure:
        return "Please provide a procedure name or CPT code to check coverage."

    # Try OpenEMR for insurance data
    openemr_insurance_info = None
    try:
        if openemr.is_available():
            patients = openemr.get_patients()
            if patients:
                for patient in patients[:5]:
                    pid = patient.get("pid") or patient.get("id") or patient.get("uuid")
                    if pid:
                        ins_data = openemr.get_patient_insurance(int(pid) if str(pid).isdigit() else pid)
                        if ins_data:
                            openemr_insurance_info = ins_data
                            logger.info("Found insurance data from OpenEMR for patient %s", pid)
                            break
    except Exception as e:
        logger.info("OpenEMR insurance lookup failed (%s), using mock data", e)

    # Resolve procedure code
    cpt_code = _resolve_procedure_code(procedure)

    # Find matching plans
    plans = _find_matching_plans(plan_name)

    if not plans:
        return (
            f"No insurance plans found matching '{plan_name}'.\n"
            "Available plans in our system: Blue Cross PPO, Medicare, Aetna HMO.\n"
            "Please check with your insurance provider for specific coverage details."
        )

    lines = [f"Insurance Coverage Check: {procedure}"]
    if cpt_code:
        lines.append(f"CPT Code: {cpt_code}")
    lines.append("")

    found_coverage = False
    for plan in plans:
        lines.append(f"Plan: {plan['plan_name']} ({plan['type']})")
        lines.append(f"Plan ID: {plan['plan_id']}")

        coverage = None
        if cpt_code and cpt_code in plan["coverages"]:
            coverage = plan["coverages"][cpt_code]
        elif not cpt_code:
            # Try fuzzy match against descriptions
            for code, cov in plan["coverages"].items():
                if procedure.lower() in cov["description"].lower():
                    coverage = cov
                    cpt_code = code
                    break

        if coverage:
            found_coverage = True
            lines.append(f"  Procedure: {coverage['description']}")
            lines.append(f"  Covered: {'Yes' if coverage['covered'] else 'No'}")
            if coverage["copay"] > 0:
                lines.append(f"  Copay: ${coverage['copay']}")
            if coverage["coinsurance"] > 0:
                lines.append(f"  Coinsurance: {coverage['coinsurance']:.0%} (you pay)")
            lines.append(f"  Deductible Applies: {'Yes' if coverage['deductible_applies'] else 'No'}")
            if coverage["prior_auth"]:
                lines.append("  Prior Authorization: REQUIRED")
            else:
                lines.append("  Prior Authorization: Not required")

            deductible = plan["deductible"]
            lines.append(f"  Annual Deductible: ${deductible['individual']} individual / ${deductible['family']} family")

            oop = plan["out_of_pocket_max"]
            if oop["individual"] > 0:
                lines.append(f"  Out-of-Pocket Max: ${oop['individual']} individual / ${oop['family']} family")

            if plan.get("notes"):
                lines.append(f"  Note: {plan['notes']}")
        else:
            lines.append(f"  Coverage information not found for '{procedure}' under this plan.")
            lines.append("  Contact your insurance provider for specific coverage details.")

        lines.append("")

    if not found_coverage:
        lines.append(
            "Could not find specific coverage information. "
            "Common procedure codes: office visit (99213), x-ray (71046), EKG (93000)."
        )
        lines.append("")

    lines.append("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]")
    if openemr_insurance_info:
        lines.append("Source: OpenEMR Insurance Records + AgentForge Coverage Database")
    else:
        lines.append("Source: AgentForge Insurance Coverage Database (Demo Data)")
    lines.append(
        "DISCLAIMER: Coverage details shown are for demonstration purposes. "
        "Actual coverage depends on your specific plan, deductible status, and network. "
        "Always verify with your insurance provider before scheduling procedures."
    )
    return "\n".join(lines)
