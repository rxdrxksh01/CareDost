import os
import pickle
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.pickle"
CALENDAR_ID = "sharmarudraksh1001@gmail.com"

FREE_START_HOUR = 16
FREE_END_HOUR = 19
MAX_SLOTS_PER_DAY = 5

IST = timezone(timedelta(hours=5, minutes=30))

def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES,
                redirect_uri="http://localhost:8080/"
            )
            creds = flow.run_local_server(port=8080)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
    return build("calendar", "v3", credentials=creds)

def get_busy_times(date: datetime):
    try:
        service = get_calendar_service()

        day_start_ist = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=IST)
        day_end_ist = datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=IST)

        day_start_utc = day_start_ist.astimezone(timezone.utc)
        day_end_utc = day_end_ist.astimezone(timezone.utc)

        body = {
            "timeMin": day_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timeMax": day_end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timeZone": "Asia/Kolkata",
            "items": [{"id": CALENDAR_ID}]
        }

        result = service.freebusy().query(body=body).execute()
        busy = result.get("calendars", {}).get(CALENDAR_ID, {}).get("busy", [])

        busy_periods = []
        for period in busy:
            start_ist = datetime.fromisoformat(period["start"]).astimezone(IST).replace(tzinfo=None)
            end_ist = datetime.fromisoformat(period["end"]).astimezone(IST).replace(tzinfo=None)
            busy_periods.append((start_ist, end_ist))
            logger.info(f"Busy IST: {start_ist} → {end_ist}")

        return busy_periods

    except Exception as e:
        logger.error(f"Error fetching calendar: {e}")
        return []

    except Exception as e:
        logger.error(f"Error fetching calendar: {e}")
        return []

def get_available_slots_from_calendar(days_ahead=2):
    slots = []
    now = datetime.now(IST).replace(tzinfo=None)

    for day_offset in range(days_ahead):
        # Start from tomorrow to avoid near-time confusion for patients.
        date = now + timedelta(days=day_offset + 1)
        busy_periods = get_busy_times(date)
        day_slots = 0

        for hour in range(FREE_START_HOUR, FREE_END_HOUR):
            if day_slots >= MAX_SLOTS_PER_DAY:
                break

            slot_time = date.replace(
                hour=hour, minute=0, second=0, microsecond=0
            )

            if slot_time <= now:
                continue

            # compare as naive datetimes
            is_busy = False
            for busy_start, busy_end in busy_periods:
                if busy_start <= slot_time < busy_end:
                    is_busy = True
                    break

            if not is_busy:
                slots.append({
                    "id": len(slots) + 1,
                    "time": slot_time.strftime("%d %b, %I:%M %p"),
                    "datetime": slot_time
                })
                day_slots += 1

    return slots

def book_slot_on_calendar(apt_time: datetime, patient_name: str, doctor_name: str):
    try:
        service = get_calendar_service()
        event = {
            "summary": f"Appointment — {patient_name}",
            "description": f"CareDost booking\nDoctor: {doctor_name}\nPatient: {patient_name}",
            "start": {
                "dateTime": apt_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Asia/Kolkata"
            },
            "end": {
                "dateTime": (apt_time + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Asia/Kolkata"
            }
        }
        result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        event_id = result.get("id")
        logger.info(f"Calendar event {event_id} created for {patient_name} at {apt_time}")
        return event_id
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        return None

def delete_event_from_calendar(event_id: str):
    if not event_id:
        return False
    try:
        service = get_calendar_service()
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        logger.info(f"Calendar event {event_id} deleted successfully.")
        return True
    except Exception as e:
        # Ignore 410 Gone (already deleted) or 404
        if "410" in str(e) or "404" in str(e):
            return True
        logger.error(f"Failed to delete calendar event {event_id}: {e}")
        return False