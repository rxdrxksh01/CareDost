import logging
from datetime import datetime
from db.database import SessionLocal
from db.models import Patient, MedicationReminder, Appointment, VisitSummary

logger = logging.getLogger(__name__)

async def notify_patient_visit_complete(bot, appointment_id: int):
    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()

        if not apt:
            return

        patient = db.query(Patient).filter(
            Patient.id == apt.patient_id
        ).first()

        summary = db.query(VisitSummary).filter(
            VisitSummary.appointment_id == appointment_id
        ).first()

        if not patient or not summary:
            return

        # build message
        msg = f"🏥 *Visit Summary — CareDost*\n\n"
        msg += f"📅 {apt.appointment_time.strftime('%d %b %Y, %I:%M %p')}\n\n"

        if summary.notes:
            msg += f"📋 *Diagnosis:*\n{summary.notes}\n\n"

        if summary.medicines:
            msg += f"💊 *Medicines Prescribed:*\n{summary.medicines}\n\n"

        if summary.follow_up_date:
            msg += f"🔄 *Follow-up:* {summary.follow_up_date.strftime('%d %b %Y')}\n\n"

        msg += "Take your medicines on time. Get well soon! 🙏"

        await bot.send_message(
            chat_id=patient.telegram_id,
            text=msg,
            parse_mode="Markdown"
        )
        logger.info(f"Visit summary sent to {patient.name}")

    except Exception as e:
        logger.error(f"Failed to send visit summary: {e}")
    finally:
        db.close()

async def send_medication_reminders(bot):
    db = SessionLocal()
    try:
        now = datetime.now()
        current_hour = now.hour

        # map hour to timing
        if 6 <= current_hour < 11:
            timing = "morning"
        elif 11 <= current_hour < 15:
            timing = "afternoon"
        elif 15 <= current_hour < 19:
            timing = "evening"
        elif 19 <= current_hour < 23:
            timing = "night"
        else:
            db.close()
            return

        reminders = db.query(MedicationReminder).filter(
            MedicationReminder.active == True,
            MedicationReminder.timing == timing,
            MedicationReminder.start_date <= now,
            MedicationReminder.end_date >= now
        ).all()

        for reminder in reminders:
            patient = db.query(Patient).filter(
                Patient.id == reminder.patient_id
            ).first()

            if not patient:
                continue

            try:
                await bot.send_message(
                    chat_id=patient.telegram_id,
                    text=(
                        f"💊 *Medication Reminder*\n\n"
                        f"Time to take your *{reminder.medicine_name}*\n\n"
                        f"⏰ {timing.capitalize()} dose\n\n"
                        f"Stay consistent for a faster recovery! 💪"
                    ),
                    parse_mode="Markdown"
                )
                logger.info(f"Med reminder sent to {patient.name} for {reminder.medicine_name}")
            except Exception as e:
                logger.error(f"Failed to send med reminder to {patient.telegram_id}: {e}")

    except Exception as e:
        logger.error(f"Error in send_medication_reminders: {e}")
    finally:
        db.close()