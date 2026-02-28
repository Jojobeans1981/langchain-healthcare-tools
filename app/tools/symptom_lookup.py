import json
import logging
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Emergency symptoms that require immediate escalation
EMERGENCY_KEYWORDS = [
    "chest pain",
    "difficulty breathing",
    "shortness of breath",
    "severe bleeding",
    "loss of consciousness",
    "sudden numbness",
    "sudden confusion",
    "slurred speech",
    "severe allergic reaction",
    "anaphylaxis",
    "suicidal",
    "self-harm",
    "overdose",
    "seizure",
    "stroke symptoms",
    "heart attack",
]


def _load_symptom_db() -> dict:
    """Load the symptom-condition mapping database."""
    db_path = DATA_DIR / "symptom_conditions.json"
    if db_path.exists():
        with open(db_path) as f:
            return json.load(f)
    return _get_default_symptom_db()


def _get_default_symptom_db() -> dict:
    """Built-in symptom-condition mappings from public health sources."""
    return {
        "headache": {
            "conditions": [
                {
                    "name": "Tension Headache",
                    "likelihood": "Common",
                    "description": "Dull, aching pain often caused by stress, poor posture, or lack of sleep.",
                    "recommended_actions": [
                        "Rest in a quiet, dark room",
                        "Over-the-counter pain relievers (acetaminophen, ibuprofen)",
                        "Stay hydrated",
                        "Apply cold or warm compress",
                    ],
                },
                {
                    "name": "Migraine",
                    "likelihood": "Common",
                    "description": "Throbbing pain, often on one side, may include nausea, light/sound sensitivity.",
                    "recommended_actions": [
                        "Rest in a dark, quiet room",
                        "OTC pain relievers or prescribed triptans",
                        "Stay hydrated",
                        "See a doctor if migraines are frequent (>4/month)",
                    ],
                },
                {
                    "name": "Sinusitis",
                    "likelihood": "Moderate",
                    "description": "Pain/pressure around forehead, cheeks, or eyes, often with congestion.",
                    "recommended_actions": [
                        "Nasal saline irrigation",
                        "Decongestants",
                        "See a doctor if lasting >10 days",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Sudden, severe 'thunderclap' headache",
                "Headache with fever, stiff neck, confusion",
                "Headache after head injury",
                "Headache with vision changes or weakness",
            ],
        },
        "fever": {
            "conditions": [
                {
                    "name": "Viral Infection (Cold/Flu)",
                    "likelihood": "Very Common",
                    "description": "Fever with body aches, fatigue, cough, or sore throat.",
                    "recommended_actions": [
                        "Rest and stay hydrated",
                        "Acetaminophen or ibuprofen for fever",
                        "Monitor temperature",
                        "See doctor if fever >103F or lasts >3 days",
                    ],
                },
                {
                    "name": "Bacterial Infection",
                    "likelihood": "Moderate",
                    "description": "High fever, possibly with localized symptoms (ear pain, urinary symptoms, etc).",
                    "recommended_actions": [
                        "See a healthcare provider",
                        "May require antibiotics",
                        "Do not self-treat with leftover antibiotics",
                    ],
                },
                {
                    "name": "COVID-19",
                    "likelihood": "Moderate",
                    "description": "Fever with cough, loss of taste/smell, fatigue, body aches.",
                    "recommended_actions": [
                        "Get tested",
                        "Isolate if positive",
                        "Rest and hydrate",
                        "Seek care if difficulty breathing",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Temperature above 104F (40C)",
                "Fever with severe headache and stiff neck",
                "Fever with rash that doesn't blanch",
                "Fever in infant under 3 months",
            ],
        },
        "cough": {
            "conditions": [
                {
                    "name": "Upper Respiratory Infection",
                    "likelihood": "Very Common",
                    "description": "Cough with runny nose, sore throat, mild fever.",
                    "recommended_actions": [
                        "Rest and fluids",
                        "Honey for cough (adults only)",
                        "OTC cough suppressants",
                        "See doctor if lasting >3 weeks",
                    ],
                },
                {
                    "name": "Allergies",
                    "likelihood": "Common",
                    "description": "Dry cough with sneezing, itchy eyes, worse seasonally or around triggers.",
                    "recommended_actions": [
                        "Antihistamines",
                        "Avoid known allergens",
                        "Nasal corticosteroid spray",
                    ],
                },
                {
                    "name": "Asthma",
                    "likelihood": "Moderate",
                    "description": "Cough with wheezing, chest tightness, worse at night or with exercise.",
                    "recommended_actions": [
                        "See a healthcare provider for diagnosis",
                        "Inhaler if prescribed",
                        "Avoid triggers",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Coughing up blood",
                "Severe difficulty breathing",
                "Cough with high fever and chest pain",
                "Blue lips or fingertips",
            ],
        },
        "stomach pain": {
            "conditions": [
                {
                    "name": "Gastritis/Indigestion",
                    "likelihood": "Very Common",
                    "description": "Upper abdominal pain, bloating, nausea, often related to food.",
                    "recommended_actions": [
                        "Antacids",
                        "Avoid spicy/fatty foods",
                        "Eat smaller meals",
                        "See doctor if persistent",
                    ],
                },
                {
                    "name": "Gastroenteritis (Stomach Flu)",
                    "likelihood": "Common",
                    "description": "Stomach cramps with diarrhea, nausea, vomiting.",
                    "recommended_actions": [
                        "Stay hydrated (oral rehydration solution)",
                        "BRAT diet",
                        "Rest",
                        "See doctor if signs of dehydration",
                    ],
                },
                {
                    "name": "Appendicitis",
                    "likelihood": "Less Common",
                    "description": "Pain starting around navel, moving to lower right. Worsens over hours.",
                    "recommended_actions": ["Seek immediate medical attention", "Do NOT take pain relievers", "Do NOT eat or drink"],
                },
            ],
            "seek_emergency_if": [
                "Severe, sudden abdominal pain",
                "Pain with fever and vomiting",
                "Abdominal pain with bloody stool",
                "Pain with inability to pass gas or stool",
            ],
        },
        "fatigue": {
            "conditions": [
                {
                    "name": "Sleep Deprivation",
                    "likelihood": "Very Common",
                    "description": "Tiredness from insufficient or poor quality sleep.",
                    "recommended_actions": [
                        "Aim for 7-9 hours of sleep",
                        "Maintain consistent sleep schedule",
                        "Limit caffeine and screens before bed",
                    ],
                },
                {
                    "name": "Anemia",
                    "likelihood": "Common",
                    "description": "Fatigue with pale skin, shortness of breath, dizziness.",
                    "recommended_actions": [
                        "See doctor for blood test",
                        "Iron-rich foods",
                        "Iron supplements if prescribed",
                    ],
                },
                {
                    "name": "Thyroid Disorder",
                    "likelihood": "Moderate",
                    "description": "Persistent fatigue with weight changes, temperature sensitivity.",
                    "recommended_actions": [
                        "See doctor for thyroid function test",
                        "Medication if diagnosed",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Sudden extreme fatigue with chest pain",
                "Fatigue with confusion or difficulty speaking",
                "Fatigue with severe shortness of breath",
            ],
        },
    }


class SymptomLookupInput(BaseModel):
    symptoms: str = Field(
        description="Description of symptoms the patient is experiencing (e.g. 'persistent headache with fever')"
    )


@tool(args_schema=SymptomLookupInput)
async def symptom_lookup(symptoms: str) -> str:
    """Look up possible conditions based on patient symptoms.

    Maps symptoms to potential conditions with likelihood, recommended actions,
    and emergency warning signs. Use this when a patient describes symptoms
    and wants to understand possible causes.
    """
    symptoms_lower = symptoms.lower()

    # Check for emergency symptoms first
    emergency_matches = [kw for kw in EMERGENCY_KEYWORDS if kw in symptoms_lower]
    if emergency_matches:
        matched = ", ".join(emergency_matches)
        return (
            f"EMERGENCY ALERT: The symptoms described ({matched}) may indicate a medical emergency.\n\n"
            "CALL 911 or go to the nearest emergency room immediately.\n\n"
            "Do NOT wait for an online consultation.\n"
            "If someone is having a heart attack or stroke, every minute counts.\n\n"
            "Source: American Heart Association, CDC Emergency Guidelines"
        )

    db = _load_symptom_db()

    # Find matching symptom categories
    matched_conditions = []
    matched_categories = []
    for symptom_key, data in db.items():
        if symptom_key in symptoms_lower:
            matched_categories.append(symptom_key)
            matched_conditions.append(data)

    if not matched_conditions:
        return (
            f"I could not find specific condition matches for: '{symptoms}'\n\n"
            "Recommendations:\n"
            "- If symptoms are mild, monitor for 24-48 hours\n"
            "- Keep a symptom diary (when, how severe, what helps)\n"
            "- Schedule an appointment with your primary care provider\n"
            "- If symptoms worsen or you develop fever, seek medical attention\n\n"
            "DISCLAIMER: This tool provides general health information only. "
            "It is not a substitute for professional medical advice."
        )

    lines = [
        f"SYMPTOM ANALYSIS RESULTS — Patient reported: '{symptoms}'",
        f"Matched symptom categories: {', '.join(matched_categories)}",
        f"IMPORTANT: In your response, reference the patient's {', '.join(matched_categories)} symptoms using their exact words.",
        "",
    ]

    for i, data in enumerate(matched_conditions):
        if i > 0:
            lines.append("---")

        lines.append("POSSIBLE CONDITIONS:")
        for condition in data["conditions"]:
            lines.append(f"\n  {condition['name']} (Likelihood: {condition['likelihood']})")
            lines.append(f"  Description: {condition['description']}")
            lines.append("  Recommended Actions:")
            for action in condition["recommended_actions"]:
                lines.append(f"    - {action}")

        if data.get("seek_emergency_if"):
            lines.append("\nSEEK EMERGENCY CARE IF:")
            for warning in data["seek_emergency_if"]:
                lines.append(f"  - {warning}")

    lines.append("")
    lines.append("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]")
    lines.append("Source: CDC, NIH MedlinePlus, Mayo Clinic general health guidelines")
    lines.append(
        "DISCLAIMER: This information is for educational purposes only. "
        "It is not a diagnosis. Always consult a healthcare professional for medical advice."
    )
    return "\n".join(lines)
