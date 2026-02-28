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


# Synonym map: common terms → symptom category keys
# This lets users ask about conditions by name (e.g. "asthma") and still
# get routed to the right symptom category.
SYMPTOM_SYNONYMS = {
    "asthma": "cough",
    "wheezing": "cough",
    "wheeze": "cough",
    "breathing problems": "cough",
    "bronchitis": "cough",
    "migraine": "headache",
    "head pain": "headache",
    "tension headache": "headache",
    "indigestion": "stomach pain",
    "bloating": "stomach pain",
    "heartburn": "stomach pain",
    "acid reflux": "stomach pain",
    "gerd": "stomach pain",
    "abdominal pain": "stomach pain",
    "belly pain": "stomach pain",
    "tummy ache": "stomach pain",
    "vomiting": "nausea",
    "throwing up": "nausea",
    "motion sickness": "nausea",
    "morning sickness": "nausea",
    "exhaustion": "fatigue",
    "tired": "fatigue",
    "tiredness": "fatigue",
    "low energy": "fatigue",
    "lethargic": "fatigue",
    "vertigo": "dizziness",
    "lightheaded": "dizziness",
    "faint": "dizziness",
    "feeling faint": "dizziness",
    "lower back pain": "back pain",
    "lumbago": "back pain",
    "sciatica": "back pain",
    "spine pain": "back pain",
    "arthritis": "joint pain",
    "stiff joints": "joint pain",
    "swollen joints": "joint pain",
    "knee pain": "joint pain",
    "hip pain": "joint pain",
    "shoulder pain": "joint pain",
    "hives": "rash",
    "eczema": "rash",
    "skin rash": "rash",
    "itchy skin": "rash",
    "dermatitis": "rash",
    "strep throat": "sore throat",
    "pharyngitis": "sore throat",
    "tonsillitis": "sore throat",
    "throat pain": "sore throat",
    "panic attack": "anxiety",
    "panic": "anxiety",
    "stress": "anxiety",
    "anxious": "anxiety",
    "nervous": "anxiety",
    "worried": "anxiety",
    "chills": "fever",
    "temperature": "fever",
    "flu": "fever",
    "cold": "fever",
}


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
        "back pain": {
            "conditions": [
                {
                    "name": "Muscle Strain",
                    "likelihood": "Very Common",
                    "description": "Pain from overuse, improper lifting, or sudden movements. Usually in the lower back.",
                    "recommended_actions": [
                        "Rest for 1-2 days, then resume gentle activity",
                        "Apply ice for first 48 hours, then heat",
                        "Over-the-counter pain relievers (ibuprofen, acetaminophen)",
                        "Gentle stretching when pain allows",
                    ],
                },
                {
                    "name": "Herniated Disc",
                    "likelihood": "Moderate",
                    "description": "Sharp pain that may radiate down one leg (sciatica). Numbness or tingling in legs/feet.",
                    "recommended_actions": [
                        "See a healthcare provider for evaluation",
                        "Physical therapy",
                        "Avoid heavy lifting and prolonged sitting",
                        "Prescription pain management if needed",
                    ],
                },
                {
                    "name": "Kidney Stones/Infection",
                    "likelihood": "Less Common",
                    "description": "Severe flank pain, often one-sided, may radiate to groin. May include painful urination.",
                    "recommended_actions": [
                        "See a healthcare provider promptly",
                        "Stay well hydrated",
                        "Pain management",
                        "May require imaging and treatment",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Back pain after a fall or trauma",
                "Pain with loss of bladder or bowel control",
                "Pain with numbness or weakness in both legs",
                "Severe pain that wakes you from sleep",
            ],
        },
        "dizziness": {
            "conditions": [
                {
                    "name": "Benign Positional Vertigo (BPPV)",
                    "likelihood": "Common",
                    "description": "Brief episodes of dizziness triggered by head position changes. Room may feel like spinning.",
                    "recommended_actions": [
                        "Epley maneuver (ask provider to demonstrate)",
                        "Move head slowly when changing positions",
                        "Sit on edge of bed before standing",
                        "See ENT specialist if persistent",
                    ],
                },
                {
                    "name": "Dehydration / Low Blood Pressure",
                    "likelihood": "Common",
                    "description": "Lightheadedness especially when standing up quickly. May feel faint.",
                    "recommended_actions": [
                        "Increase fluid intake",
                        "Rise slowly from sitting or lying positions",
                        "Eat regular meals with adequate salt",
                        "See doctor if persistent",
                    ],
                },
                {
                    "name": "Inner Ear Infection (Labyrinthitis)",
                    "likelihood": "Moderate",
                    "description": "Vertigo with hearing loss or ringing in ears, often following a cold or flu.",
                    "recommended_actions": [
                        "See a healthcare provider",
                        "Antihistamines or anti-nausea medication",
                        "Rest and avoid sudden movements",
                        "Usually resolves in 1-3 weeks",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Dizziness with sudden severe headache",
                "Dizziness with slurred speech or facial drooping",
                "Dizziness with chest pain or irregular heartbeat",
                "Sudden hearing loss with vertigo",
            ],
        },
        "nausea": {
            "conditions": [
                {
                    "name": "Gastroenteritis (Stomach Bug)",
                    "likelihood": "Very Common",
                    "description": "Nausea with vomiting, diarrhea, and stomach cramps. Often viral.",
                    "recommended_actions": [
                        "Stay hydrated with small sips of clear fluids",
                        "BRAT diet (bananas, rice, applesauce, toast)",
                        "Rest",
                        "See doctor if unable to keep fluids down for 24 hours",
                    ],
                },
                {
                    "name": "Food Poisoning",
                    "likelihood": "Common",
                    "description": "Nausea and vomiting 1-6 hours after eating contaminated food.",
                    "recommended_actions": [
                        "Stay hydrated",
                        "Rest",
                        "Avoid solid food until vomiting stops",
                        "See doctor if bloody stool or fever >101.5F",
                    ],
                },
                {
                    "name": "Medication Side Effect",
                    "likelihood": "Common",
                    "description": "Nausea as a side effect of medications, especially antibiotics, NSAIDs, or new prescriptions.",
                    "recommended_actions": [
                        "Take medications with food if allowed",
                        "Do NOT stop medication without consulting your doctor",
                        "Ask pharmacist about anti-nausea options",
                        "Contact prescribing physician if severe",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Nausea with severe abdominal pain",
                "Vomiting blood or material that looks like coffee grounds",
                "Signs of severe dehydration (no urination, extreme thirst)",
                "Nausea with high fever and stiff neck",
            ],
        },
        "joint pain": {
            "conditions": [
                {
                    "name": "Osteoarthritis",
                    "likelihood": "Common",
                    "description": "Gradual joint pain and stiffness, worse with activity. Common in knees, hips, hands.",
                    "recommended_actions": [
                        "Low-impact exercise (walking, swimming)",
                        "Weight management",
                        "Over-the-counter pain relievers",
                        "See doctor for X-ray and treatment plan",
                    ],
                },
                {
                    "name": "Tendinitis / Bursitis",
                    "likelihood": "Common",
                    "description": "Pain around a joint from inflammation of tendons or bursa, often from overuse.",
                    "recommended_actions": [
                        "Rest the affected joint",
                        "Ice for 15-20 minutes several times daily",
                        "Anti-inflammatory medication",
                        "Gentle stretching as pain improves",
                    ],
                },
                {
                    "name": "Rheumatoid Arthritis",
                    "likelihood": "Less Common",
                    "description": "Symmetrical joint pain and swelling, morning stiffness lasting >30 minutes. Autoimmune.",
                    "recommended_actions": [
                        "See a rheumatologist",
                        "Blood tests (RF, anti-CCP, ESR)",
                        "Early treatment is important",
                        "Disease-modifying medications may be needed",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Sudden, severe joint pain with swelling and redness (possible gout or septic joint)",
                "Joint pain after an injury with inability to bear weight",
                "Joint pain with fever and chills",
                "Rapid joint swelling within hours",
            ],
        },
        "rash": {
            "conditions": [
                {
                    "name": "Contact Dermatitis",
                    "likelihood": "Very Common",
                    "description": "Red, itchy rash from contact with irritants or allergens (soap, plants, metals).",
                    "recommended_actions": [
                        "Identify and avoid the trigger",
                        "Hydrocortisone cream (OTC)",
                        "Cool compresses",
                        "See doctor if widespread or not improving",
                    ],
                },
                {
                    "name": "Eczema (Atopic Dermatitis)",
                    "likelihood": "Common",
                    "description": "Dry, itchy, inflamed patches. Often in skin folds. May be chronic.",
                    "recommended_actions": [
                        "Moisturize frequently with fragrance-free products",
                        "Avoid hot showers and harsh soaps",
                        "Topical corticosteroids if prescribed",
                        "See dermatologist for persistent cases",
                    ],
                },
                {
                    "name": "Drug Reaction",
                    "likelihood": "Moderate",
                    "description": "Rash appearing within days of starting a new medication. May be widespread.",
                    "recommended_actions": [
                        "Note any new medications started recently",
                        "Contact prescribing doctor immediately",
                        "Do NOT stop medication without medical advice",
                        "Seek emergency care if breathing difficulty or swelling",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Rash with difficulty breathing or throat swelling (anaphylaxis)",
                "Rash with high fever",
                "Rapidly spreading rash with blisters or peeling skin",
                "Rash that does not blanch with pressure (petechiae/purpura)",
            ],
        },
        "sore throat": {
            "conditions": [
                {
                    "name": "Viral Pharyngitis",
                    "likelihood": "Very Common",
                    "description": "Sore throat with cold symptoms (runny nose, cough, mild fever). Usually self-limiting.",
                    "recommended_actions": [
                        "Rest and stay hydrated",
                        "Warm salt water gargles",
                        "Throat lozenges or honey",
                        "OTC pain relievers if needed",
                    ],
                },
                {
                    "name": "Strep Throat",
                    "likelihood": "Common",
                    "description": "Severe sore throat with high fever, white patches on tonsils, swollen lymph nodes. No cough.",
                    "recommended_actions": [
                        "See a healthcare provider for rapid strep test",
                        "Antibiotics if positive (complete full course)",
                        "Rest and fluids",
                        "Contagious — stay home until 24 hours on antibiotics",
                    ],
                },
                {
                    "name": "Tonsillitis",
                    "likelihood": "Moderate",
                    "description": "Inflamed, swollen tonsils with pain swallowing. May be viral or bacterial.",
                    "recommended_actions": [
                        "See doctor to determine if antibiotics are needed",
                        "Soft foods and warm liquids",
                        "Pain relievers",
                        "Surgery considered only for recurrent cases",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Sore throat with difficulty breathing or swallowing",
                "Unable to open mouth fully (possible peritonsillar abscess)",
                "Drooling due to inability to swallow",
                "Sore throat with rash (possible scarlet fever)",
            ],
        },
        "anxiety": {
            "conditions": [
                {
                    "name": "Generalized Anxiety Disorder",
                    "likelihood": "Common",
                    "description": "Persistent excessive worry about multiple areas of life. May include restlessness, muscle tension, sleep difficulty.",
                    "recommended_actions": [
                        "Schedule appointment with primary care or mental health provider",
                        "Regular physical exercise",
                        "Relaxation techniques (deep breathing, meditation)",
                        "Limit caffeine and alcohol",
                    ],
                },
                {
                    "name": "Panic Disorder",
                    "likelihood": "Moderate",
                    "description": "Sudden episodes of intense fear with physical symptoms (racing heart, chest tightness, shortness of breath).",
                    "recommended_actions": [
                        "See a healthcare provider for evaluation",
                        "Cognitive behavioral therapy (CBT)",
                        "Learn grounding techniques (5-4-3-2-1 method)",
                        "Medication may be recommended",
                    ],
                },
                {
                    "name": "Situational / Stress-Related Anxiety",
                    "likelihood": "Very Common",
                    "description": "Anxiety related to specific stressors (work, relationships, health). Usually temporary.",
                    "recommended_actions": [
                        "Identify and address the stressor",
                        "Regular exercise and adequate sleep",
                        "Talk to a trusted person or counselor",
                        "Practice mindfulness or journaling",
                    ],
                },
            ],
            "seek_emergency_if": [
                "Panic symptoms that feel like a heart attack (get checked to rule out cardiac cause)",
                "Thoughts of self-harm or suicide — call 988 Suicide & Crisis Lifeline",
                "Anxiety so severe you cannot function or leave home",
                "Anxiety with substance use to cope",
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

    # Find matching symptom categories (direct key match)
    matched_conditions = []
    matched_categories = []
    matched_keys = set()
    for symptom_key, data in db.items():
        if symptom_key in symptoms_lower:
            matched_keys.add(symptom_key)
            matched_categories.append(symptom_key)
            matched_conditions.append(data)

    # Synonym matching: check if any synonym appears in the query
    # and add the corresponding category if not already matched
    for synonym, category_key in SYMPTOM_SYNONYMS.items():
        if synonym in symptoms_lower and category_key not in matched_keys:
            if category_key in db:
                matched_keys.add(category_key)
                matched_categories.append(f"{category_key} (matched via '{synonym}')")
                matched_conditions.append(db[category_key])

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
    lines.append("Source: AgentForge Symptom Database (curated from CDC, NIH MedlinePlus, Mayo Clinic public guidelines — Built-in Database)")
    lines.append(
        "DISCLAIMER: This information is for educational purposes only. "
        "It is not a diagnosis. Always consult a healthcare professional for medical advice."
    )
    return "\n".join(lines)
