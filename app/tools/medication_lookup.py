import logging

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

OPENFDA_BASE = "https://api.fda.gov/drug/label.json"

# Fallback mock data for common medications when FDA API is unavailable
MOCK_MEDICATIONS = {
    "metformin": {
        "brand_names": ["Glucophage", "Glucophage XR", "Fortamet"],
        "generic_name": "Metformin Hydrochloride",
        "manufacturer": "Bristol-Myers Squibb",
        "indications": "Treatment of type 2 diabetes mellitus to improve glycemic control in adults and pediatric patients 10 years of age and older.",
        "warnings": "Lactic acidosis is a rare but serious complication. Risk increases with renal impairment, excessive alcohol intake, hepatic insufficiency, and conditions causing hypoxemia.",
        "contraindications": "Severe renal impairment (eGFR below 30 mL/min/1.73 m2), acute or chronic metabolic acidosis including diabetic ketoacidosis.",
        "dosage_forms": "Tablets: 500mg, 850mg, 1000mg; Extended-release tablets: 500mg, 750mg, 1000mg",
        "drug_class": "Biguanide antihyperglycemic",
    },
    "lisinopril": {
        "brand_names": ["Prinivil", "Zestril"],
        "generic_name": "Lisinopril",
        "manufacturer": "Merck & Co / AstraZeneca",
        "indications": "Treatment of hypertension, heart failure, and to improve survival after myocardial infarction in hemodynamically stable patients.",
        "warnings": "Can cause fetal toxicity when administered to a pregnant woman. Angioedema may occur at any time during treatment. Hypotension risk in volume-depleted patients.",
        "contraindications": "History of angioedema related to previous ACE inhibitor treatment. Do not co-administer with aliskiren in patients with diabetes.",
        "dosage_forms": "Tablets: 2.5mg, 5mg, 10mg, 20mg, 30mg, 40mg",
        "drug_class": "ACE Inhibitor (Angiotensin-Converting Enzyme Inhibitor)",
    },
    "atorvastatin": {
        "brand_names": ["Lipitor"],
        "generic_name": "Atorvastatin Calcium",
        "manufacturer": "Pfizer",
        "indications": "Adjunct to diet for reduction of elevated total-C, LDL-C, apolipoprotein B, and triglycerides in patients with primary hypercholesterolemia and mixed dyslipidemia.",
        "warnings": "Skeletal muscle effects (myopathy/rhabdomyolysis): Risk increases with higher doses and certain interacting drugs. Liver enzyme abnormalities may occur.",
        "contraindications": "Active liver disease or unexplained persistent elevations of serum transaminases. Pregnancy and nursing mothers.",
        "dosage_forms": "Tablets: 10mg, 20mg, 40mg, 80mg",
        "drug_class": "HMG-CoA Reductase Inhibitor (Statin)",
    },
    "amoxicillin": {
        "brand_names": ["Amoxil", "Trimox"],
        "generic_name": "Amoxicillin",
        "manufacturer": "GlaxoSmithKline",
        "indications": "Treatment of infections due to susceptible organisms involving the ear, nose, throat, genitourinary tract, skin, and lower respiratory tract.",
        "warnings": "Serious and potentially fatal hypersensitivity (anaphylactic) reactions in patients on penicillin therapy. Clostridium difficile-associated diarrhea reported.",
        "contraindications": "Known serious hypersensitivity reaction to amoxicillin or other beta-lactam antibiotics.",
        "dosage_forms": "Capsules: 250mg, 500mg; Tablets: 500mg, 875mg; Oral suspension: 125mg/5mL, 250mg/5mL",
        "drug_class": "Aminopenicillin Antibiotic",
    },
    "omeprazole": {
        "brand_names": ["Prilosec", "Prilosec OTC"],
        "generic_name": "Omeprazole",
        "manufacturer": "AstraZeneca",
        "indications": "Short-term treatment of active duodenal ulcer, gastric ulcer, GERD, erosive esophagitis, and pathological hypersecretory conditions including Zollinger-Ellison syndrome.",
        "warnings": "Long-term use may increase risk of bone fractures, hypomagnesemia, Clostridium difficile-associated diarrhea, and vitamin B-12 deficiency.",
        "contraindications": "Known hypersensitivity to omeprazole or substituted benzimidazoles. Concomitant use with rilpivirine-containing products.",
        "dosage_forms": "Capsules: 10mg, 20mg, 40mg; Oral suspension packets: 2.5mg, 10mg",
        "drug_class": "Proton Pump Inhibitor (PPI)",
    },
    "amlodipine": {
        "brand_names": ["Norvasc"],
        "generic_name": "Amlodipine Besylate",
        "manufacturer": "Pfizer",
        "indications": "Treatment of hypertension and coronary artery disease (chronic stable angina and vasospastic angina).",
        "warnings": "Symptomatic hypotension is possible, particularly in patients with severe aortic stenosis. Worsening angina and acute MI can develop on starting or increasing dose.",
        "contraindications": "Known sensitivity to amlodipine.",
        "dosage_forms": "Tablets: 2.5mg, 5mg, 10mg",
        "drug_class": "Calcium Channel Blocker (Dihydropyridine)",
    },
    "losartan": {
        "brand_names": ["Cozaar"],
        "generic_name": "Losartan Potassium",
        "manufacturer": "Merck & Co",
        "indications": "Treatment of hypertension, diabetic nephropathy in type 2 diabetes, and stroke risk reduction in patients with hypertension and left ventricular hypertrophy.",
        "warnings": "Can cause fetal toxicity. Hypotension may occur in volume-depleted patients. Hyperkalemia risk, especially with renal impairment or potassium supplements.",
        "contraindications": "Pregnancy. Do not co-administer with aliskiren in patients with diabetes or renal impairment.",
        "dosage_forms": "Tablets: 25mg, 50mg, 100mg",
        "drug_class": "Angiotensin II Receptor Blocker (ARB)",
    },
    "levothyroxine": {
        "brand_names": ["Synthroid", "Levoxyl", "Tirosint"],
        "generic_name": "Levothyroxine Sodium",
        "manufacturer": "AbbVie",
        "indications": "Replacement therapy in hypothyroidism. Pituitary TSH suppression in the treatment of thyroid cancer and thyroid nodules.",
        "warnings": "Overtreatment may cause hyperthyroidism symptoms (palpitations, weight loss, tremors). Should not be used for weight loss. Requires monitoring of TSH levels.",
        "contraindications": "Uncorrected adrenal insufficiency. Acute myocardial infarction.",
        "dosage_forms": "Tablets: 25mcg, 50mcg, 75mcg, 88mcg, 100mcg, 112mcg, 125mcg, 137mcg, 150mcg, 175mcg, 200mcg, 300mcg",
        "drug_class": "Thyroid Hormone (T4)",
    },
    "sertraline": {
        "brand_names": ["Zoloft"],
        "generic_name": "Sertraline Hydrochloride",
        "manufacturer": "Pfizer",
        "indications": "Treatment of major depressive disorder, panic disorder, PTSD, OCD, social anxiety disorder, and premenstrual dysphoric disorder.",
        "warnings": "Suicidality risk in children, adolescents, and young adults. Serotonin syndrome risk with other serotonergic drugs. May cause discontinuation symptoms if stopped abruptly.",
        "contraindications": "Concurrent use with MAOIs or pimozide. Do not use within 14 days of MAOI discontinuation.",
        "dosage_forms": "Tablets: 25mg, 50mg, 100mg; Oral solution: 20mg/mL",
        "drug_class": "Selective Serotonin Reuptake Inhibitor (SSRI)",
    },
    "gabapentin": {
        "brand_names": ["Neurontin", "Gralise"],
        "generic_name": "Gabapentin",
        "manufacturer": "Pfizer",
        "indications": "Adjunctive therapy for partial seizures. Management of postherpetic neuralgia. Also used off-label for neuropathic pain and anxiety.",
        "warnings": "CNS depression, especially with opioids (risk of respiratory depression). Dizziness and somnolence. Withdrawal seizures if stopped abruptly.",
        "contraindications": "Known hypersensitivity to gabapentin.",
        "dosage_forms": "Capsules: 100mg, 300mg, 400mg; Tablets: 600mg, 800mg; Oral solution: 250mg/5mL",
        "drug_class": "Anticonvulsant / GABA Analog",
    },
    "hydrochlorothiazide": {
        "brand_names": ["Microzide", "HydroDIURIL"],
        "generic_name": "Hydrochlorothiazide",
        "manufacturer": "Various",
        "indications": "Treatment of hypertension and edema associated with heart failure, hepatic cirrhosis, and corticosteroid/estrogen therapy.",
        "warnings": "Electrolyte imbalances (hypokalemia, hyponatremia). Photosensitivity. May increase blood glucose and uric acid levels.",
        "contraindications": "Anuria. Known hypersensitivity to sulfonamide-derived drugs.",
        "dosage_forms": "Tablets: 12.5mg, 25mg, 50mg; Capsules: 12.5mg",
        "drug_class": "Thiazide Diuretic",
    },
    "prednisone": {
        "brand_names": ["Deltasone", "Rayos"],
        "generic_name": "Prednisone",
        "manufacturer": "Various",
        "indications": "Treatment of inflammatory and autoimmune conditions including asthma, COPD exacerbations, rheumatoid arthritis, lupus, and allergic reactions.",
        "warnings": "Long-term use causes adrenal suppression, osteoporosis, hyperglycemia, immunosuppression, and Cushing syndrome. Do not stop abruptly — must taper dose.",
        "contraindications": "Systemic fungal infections. Live vaccines in immunosuppressive doses.",
        "dosage_forms": "Tablets: 1mg, 2.5mg, 5mg, 10mg, 20mg, 50mg; Oral solution: 5mg/5mL",
        "drug_class": "Corticosteroid (Glucocorticoid)",
    },
    "clopidogrel": {
        "brand_names": ["Plavix"],
        "generic_name": "Clopidogrel Bisulfate",
        "manufacturer": "Sanofi / Bristol-Myers Squibb",
        "indications": "Reduction of atherothrombotic events in patients with recent MI, recent stroke, or established peripheral arterial disease. Acute coronary syndrome management.",
        "warnings": "Bleeding risk. CYP2C19 poor metabolizers have reduced effectiveness — consider alternative antiplatelet therapy. Avoid omeprazole (reduces effectiveness).",
        "contraindications": "Active pathological bleeding (peptic ulcer, intracranial hemorrhage).",
        "dosage_forms": "Tablets: 75mg, 300mg",
        "drug_class": "P2Y12 Platelet Inhibitor (Antiplatelet)",
    },
    "pantoprazole": {
        "brand_names": ["Protonix"],
        "generic_name": "Pantoprazole Sodium",
        "manufacturer": "Pfizer",
        "indications": "Short-term treatment of erosive esophagitis associated with GERD. Maintenance of healing. Zollinger-Ellison syndrome.",
        "warnings": "Long-term use associated with bone fractures, hypomagnesemia, C. difficile infection, and vitamin B-12 deficiency. Preferred PPI when used with clopidogrel.",
        "contraindications": "Known hypersensitivity to pantoprazole or substituted benzimidazoles. Concomitant rilpivirine use.",
        "dosage_forms": "Tablets: 20mg, 40mg; IV injection: 40mg vial",
        "drug_class": "Proton Pump Inhibitor (PPI)",
    },
    "tramadol": {
        "brand_names": ["Ultram", "ConZip"],
        "generic_name": "Tramadol Hydrochloride",
        "manufacturer": "Various",
        "indications": "Management of moderate to moderately severe pain in adults. Extended-release for around-the-clock pain management.",
        "warnings": "Risk of seizures, especially with SSRIs/SNRIs. Serotonin syndrome risk. Respiratory depression risk, especially with CNS depressants. Risk of misuse and dependence.",
        "contraindications": "Significant respiratory depression. Acute or severe bronchial asthma without monitoring. Concurrent or recent (within 14 days) MAOI use.",
        "dosage_forms": "Tablets: 50mg; Extended-release tablets: 100mg, 200mg, 300mg",
        "drug_class": "Opioid Analgesic (Centrally Acting)",
    },
}


class MedicationLookupInput(BaseModel):
    drug_name: str = Field(description="Name of the medication to look up (brand or generic name, e.g. 'metformin', 'Lipitor')")


def _parse_fda_label(result: dict) -> dict:
    """Extract key information from an OpenFDA drug label result."""
    openfda = result.get("openfda", {})
    return {
        "brand_names": openfda.get("brand_name", ["Unknown"]),
        "generic_name": openfda.get("generic_name", ["Unknown"])[0] if openfda.get("generic_name") else "Unknown",
        "manufacturer": openfda.get("manufacturer_name", ["Unknown"])[0] if openfda.get("manufacturer_name") else "Unknown",
        "indications": (result.get("indications_and_usage", ["Not available"])[0])[:500],
        "warnings": (result.get("warnings", result.get("warnings_and_cautions", ["Not available"]))[0])[:500],
        "contraindications": (result.get("contraindications", ["Not available"])[0])[:500],
        "dosage_forms": (result.get("dosage_forms_and_strengths", result.get("dosage_and_administration", ["Not available"]))[0])[:300],
        "drug_class": openfda.get("pharm_class_epc", ["Not classified"])[0] if openfda.get("pharm_class_epc") else "Not classified",
    }


def _check_mock_data(drug_name: str) -> dict | None:
    """Check local mock data for common medications."""
    name_lower = drug_name.strip().lower()
    if name_lower in MOCK_MEDICATIONS:
        return MOCK_MEDICATIONS[name_lower]
    # Check brand names
    for generic, data in MOCK_MEDICATIONS.items():
        for brand in data["brand_names"]:
            if brand.lower() == name_lower:
                return data
    return None


@tool(args_schema=MedicationLookupInput)
async def medication_lookup(drug_name: str) -> str:
    """Look up detailed medication information from the FDA database.

    Returns drug indications, warnings, contraindications, dosage forms,
    and manufacturer information. Use this tool when patients ask about
    a specific medication's purpose, side effects, or general information.
    """
    if not drug_name or not drug_name.strip():
        return "Please provide a medication name to look up."

    drug_name = drug_name.strip()
    source = "FDA OpenFDA Drug Label Database"
    med_info = None

    # Try FDA OpenFDA API first
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Search by brand name first, then generic
            for field in ["openfda.brand_name", "openfda.generic_name"]:
                resp = await client.get(
                    OPENFDA_BASE,
                    params={"search": f'{field}:"{drug_name}"', "limit": 1},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if results:
                        med_info = _parse_fda_label(results[0])
                        break
    except Exception as e:
        logger.warning("OpenFDA API error for %s: %s", drug_name, e)

    # Fall back to mock data
    if not med_info:
        med_info = _check_mock_data(drug_name)
        if med_info:
            source = "AgentForge Medication Database (Demo Data)"

    if not med_info:
        return (
            f"Medication '{drug_name}' not found in FDA database.\n\n"
            "Please check the spelling or try the generic/brand name.\n"
            "Common medications in our database: metformin, lisinopril, atorvastatin (Lipitor), "
            "amoxicillin, omeprazole (Prilosec), amlodipine (Norvasc).\n\n"
            "Source: FDA OpenFDA API\n"
            "DISCLAIMER: Always consult your pharmacist or healthcare provider for medication information."
        )

    # Format response
    brand_str = ", ".join(med_info["brand_names"]) if isinstance(med_info["brand_names"], list) else med_info["brand_names"]
    lines = [
        f"Medication Information: {drug_name}",
        "",
        f"Generic Name: {med_info['generic_name']}",
        f"Brand Name(s): {brand_str}",
        f"Drug Class: {med_info['drug_class']}",
        f"Manufacturer: {med_info['manufacturer']}",
        "",
        f"Indications: {med_info['indications']}",
        "",
        f"Key Warnings: {med_info['warnings']}",
        "",
        f"Contraindications: {med_info['contraindications']}",
        "",
        f"Dosage Forms: {med_info['dosage_forms']}",
        "",
        "[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]",
        f"Source: {source}",
        "DISCLAIMER: This information is for educational purposes only. "
        "Do not start, stop, or change any medication without consulting your healthcare provider.",
    ]
    return "\n".join(lines)
