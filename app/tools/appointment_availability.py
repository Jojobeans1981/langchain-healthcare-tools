import logging
from datetime import datetime, timedelta

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.openemr_client import openemr

logger = logging.getLogger(__name__)

# Mock appointment slots used when OpenEMR is unavailable
MOCK_AVAILABILITY = {
    "Cardiology": [
        {"provider": "Dr. Sarah Chen", "date": "2026-03-03", "time": "09:00 AM", "duration": 30},
        {"provider": "Dr. Sarah Chen", "date": "2026-03-03", "time": "10:30 AM", "duration": 30},
        {"provider": "Dr. Sarah Chen", "date": "2026-03-05", "time": "02:00 PM", "duration": 30},
        {"provider": "Dr. Sarah Chen", "date": "2026-03-06", "time": "09:00 AM", "duration": 30},
    ],
    "Family Medicine": [
        {"provider": "Dr. James Wilson", "date": "2026-03-03", "time": "08:00 AM", "duration": 20},
        {"provider": "Dr. James Wilson", "date": "2026-03-03", "time": "11:00 AM", "duration": 20},
        {"provider": "Dr. James Wilson", "date": "2026-03-04", "time": "09:00 AM", "duration": 20},
        {"provider": "Dr. James Wilson", "date": "2026-03-04", "time": "01:00 PM", "duration": 20},
        {"provider": "Dr. James Wilson", "date": "2026-03-05", "time": "10:00 AM", "duration": 20},
    ],
    "Neurology": [
        {"provider": "Dr. Maria Garcia", "date": "2026-03-04", "time": "10:00 AM", "duration": 45},
        {"provider": "Dr. Maria Garcia", "date": "2026-03-06", "time": "11:00 AM", "duration": 45},
        {"provider": "Dr. Maria Garcia", "date": "2026-03-07", "time": "09:00 AM", "duration": 45},
    ],
    "Dermatology": [
        {"provider": "Dr. Robert Kim", "date": "2026-03-10", "time": "09:00 AM", "duration": 15},
        {"provider": "Dr. Robert Kim", "date": "2026-03-10", "time": "09:30 AM", "duration": 15},
        {"provider": "Dr. Robert Kim", "date": "2026-03-10", "time": "10:00 AM", "duration": 15},
    ],
    "Pediatrics": [
        {"provider": "Dr. Emily Thompson", "date": "2026-03-03", "time": "08:30 AM", "duration": 20},
        {"provider": "Dr. Emily Thompson", "date": "2026-03-03", "time": "01:00 PM", "duration": 20},
        {"provider": "Dr. Emily Thompson", "date": "2026-03-04", "time": "09:00 AM", "duration": 20},
        {"provider": "Dr. Emily Thompson", "date": "2026-03-05", "time": "11:00 AM", "duration": 20},
    ],
    "Psychiatry": [
        {"provider": "Dr. Linda Patel", "date": "2026-03-04", "time": "10:00 AM", "duration": 50},
        {"provider": "Dr. Linda Patel", "date": "2026-03-05", "time": "02:00 PM", "duration": 50},
        {"provider": "Dr. Linda Patel", "date": "2026-03-07", "time": "10:00 AM", "duration": 50},
    ],
}


class AppointmentAvailabilityInput(BaseModel):
    specialty: str = Field(description="Medical specialty to search for (e.g. 'Cardiology', 'Family Medicine')")
    date_range_days: int = Field(default=7, description="Number of days ahead to search for availability (default: 7)")


@tool(args_schema=AppointmentAvailabilityInput)
async def appointment_availability(specialty: str, date_range_days: int = 7) -> str:
    """Check appointment availability for a given medical specialty.

    Searches the OpenEMR scheduling system for available appointment slots
    within the specified date range. Use this when a patient wants to
    schedule an appointment or check available times.
    """
    if not specialty:
        return "Please provide a medical specialty to search for available appointments."

    # Try OpenEMR first
    slots = []
    source = "OpenEMR Scheduling System"
    try:
        results = openemr.get_appointments()
        if results:
            slots = [
                {
                    "provider": appt.get("pc_aid_name", "") or appt.get("provider", "Unknown"),
                    "date": appt.get("pc_eventDate", ""),
                    "time": appt.get("pc_startTime", ""),
                    "duration": int(appt.get("pc_duration", 1800)) // 60,
                }
                for appt in results
            ]
    except Exception as e:
        logger.info("OpenEMR unavailable (%s), using mock data", e)

    # Fall back to mock data
    if not slots:
        source = "AgentForge Demo Scheduling System"
        specialty_lower = specialty.lower()
        for key, avail in MOCK_AVAILABILITY.items():
            if specialty_lower in key.lower():
                slots = avail
                break

    if not slots:
        return (
            f"No available appointments found for '{specialty}' in the next {date_range_days} days.\n\n"
            "Suggestions:\n"
            "- Try a broader specialty term\n"
            "- Extend the date range\n"
            "- Call the provider's office directly for waitlist options\n"
            "- Consider urgent care for immediate needs"
        )

    # Filter by date range
    today = datetime.now()
    end_date = today + timedelta(days=date_range_days)
    filtered = []
    for slot in slots:
        try:
            slot_date = datetime.strptime(slot["date"], "%Y-%m-%d")
            if today <= slot_date <= end_date:
                filtered.append(slot)
        except ValueError:
            filtered.append(slot)

    display_slots = filtered if filtered else slots

    lines = [
        f"APPOINTMENT RESULTS FOR {specialty.upper()}:",
        f"Found {len(display_slots)} available slot(s). YOU MUST LIST ALL OF THESE TO THE USER:",
        "",
    ]

    for i, slot in enumerate(display_slots, 1):
        lines.append(f"  Slot {i}: {slot['date']} at {slot['time']} with {slot['provider']} ({slot['duration']} min)")

    lines.append("")
    lines.append("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]")
    lines.append(f"Source: {source}")
    return "\n".join(lines)
