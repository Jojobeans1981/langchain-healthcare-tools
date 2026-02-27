import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.openemr_client import openemr

logger = logging.getLogger(__name__)

# Mock provider data used when OpenEMR is unavailable
MOCK_PROVIDERS = [
    {
        "id": "prov-001",
        "name": "Dr. Sarah Chen",
        "specialty": "Cardiology",
        "facility": "City Heart Center",
        "phone": "(555) 100-2001",
        "accepting_new_patients": True,
    },
    {
        "id": "prov-002",
        "name": "Dr. James Wilson",
        "specialty": "Family Medicine",
        "facility": "Downtown Family Clinic",
        "phone": "(555) 100-2002",
        "accepting_new_patients": True,
    },
    {
        "id": "prov-003",
        "name": "Dr. Maria Garcia",
        "specialty": "Neurology",
        "facility": "Metro Neuroscience Institute",
        "phone": "(555) 100-2003",
        "accepting_new_patients": True,
    },
    {
        "id": "prov-004",
        "name": "Dr. Robert Kim",
        "specialty": "Dermatology",
        "facility": "Skin Health Associates",
        "phone": "(555) 100-2004",
        "accepting_new_patients": False,
    },
    {
        "id": "prov-005",
        "name": "Dr. Emily Thompson",
        "specialty": "Pediatrics",
        "facility": "Children's Wellness Center",
        "phone": "(555) 100-2005",
        "accepting_new_patients": True,
    },
    {
        "id": "prov-006",
        "name": "Dr. Michael Brown",
        "specialty": "Orthopedics",
        "facility": "Sports Medicine & Joint Care",
        "phone": "(555) 100-2006",
        "accepting_new_patients": True,
    },
    {
        "id": "prov-007",
        "name": "Dr. Linda Patel",
        "specialty": "Psychiatry",
        "facility": "Mindful Health Clinic",
        "phone": "(555) 100-2007",
        "accepting_new_patients": True,
    },
    {
        "id": "prov-008",
        "name": "Dr. David Lee",
        "specialty": "Gastroenterology",
        "facility": "Digestive Health Center",
        "phone": "(555) 100-2008",
        "accepting_new_patients": True,
    },
]


class ProviderSearchInput(BaseModel):
    specialty: str = Field(default="", description="Medical specialty to search for (e.g. 'Cardiology', 'Family Medicine')")
    name: str = Field(default="", description="Provider name to search for")


@tool(args_schema=ProviderSearchInput)
async def provider_search(specialty: str = "", name: str = "") -> str:
    """Search for healthcare providers by specialty or name.

    Queries the OpenEMR system for matching practitioners. Use this when
    a patient needs to find a doctor, specialist, or healthcare provider.
    """
    if not specialty and not name:
        return "Please provide a specialty or provider name to search for."

    # Try OpenEMR first
    providers = []
    source = "OpenEMR"
    try:
        results = openemr.get_practitioners(specialty=specialty or None)
        if results:
            # Filter by name if provided
            if name:
                name_lower = name.lower()
                results = [
                    p for p in results
                    if name_lower in (p.get("fname", "") + " " + p.get("lname", "")).lower()
                    or name_lower in (p.get("name", "") or "").lower()
                ]
            # Normalize OpenEMR practitioner format to match tool output
            providers = [
                {
                    "id": p.get("id", ""),
                    "name": f"{p.get('fname', '')} {p.get('lname', '')}".strip() or p.get("name", "Unknown"),
                    "specialty": p.get("specialty", "") or p.get("physician_type", "") or specialty,
                    "facility": p.get("facility", ""),
                    "phone": p.get("phone", ""),
                    "accepting_new_patients": p.get("accepting_new_patients", True),
                }
                for p in results
            ]
    except Exception as e:
        logger.info("OpenEMR unavailable (%s), using mock data", e)

    # Fall back to mock data
    if not providers:
        source = "AgentForge Provider Directory (Demo Data)"
        search_lower = (specialty + " " + name).lower()
        providers = [
            p for p in MOCK_PROVIDERS
            if (specialty.lower() in p["specialty"].lower() if specialty else True)
            and (name.lower() in p["name"].lower() if name else True)
        ]

    if not providers:
        search_term = specialty or name
        return (
            f"No providers found matching '{search_term}'.\n"
            "Suggestions:\n"
            "- Try a broader specialty term\n"
            "- Check the spelling of the provider name\n"
            "- Ask your insurance company for in-network providers"
        )

    search_term = specialty or name
    lines = [f"PROVIDER RESULTS FOR '{search_term.upper()}':", f"Found {len(providers)} provider(s). YOU MUST LIST ALL OF THESE TO THE USER:", ""]

    for i, prov in enumerate(providers, 1):
        parts = [f"  Provider {i}: {prov.get('name', 'Unknown')}"]
        if prov.get("specialty"):
            parts.append(f"Specialty: {prov['specialty']}")
        if prov.get("facility"):
            parts.append(f"Facility: {prov['facility']}")
        if prov.get("phone"):
            parts.append(f"Phone: {prov['phone']}")
        if "accepting_new_patients" in prov:
            parts.append(f"Accepting New Patients: {'Yes' if prov['accepting_new_patients'] else 'No'}")
        lines.append(" | ".join(parts))

    lines.append("")
    lines.append("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]")
    lines.append(f"Source: {source}")
    return "\n".join(lines)
