from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.database import SessionLocal
from db.models import Appointment, Patient
from datetime import datetime, timedelta

scheduler = AsyncIOScheduler()

async def send_reminders(bot):
    db = SessionLocal()
    now = datetime.now()
    reminder_window = now + timedelta(hours=2)

    appointments = db.query(Appointment).filter(
        Appointment.status == "scheduled",
        Appointment.reminder_sent == False,
        Appointment.appointment_time >= now,
        Appointment.appointment_time <= reminder_window + timedelta(minutes=5)
    ).all()

    for apt in appointments:
        patient = db.query(Patient).filter(
            Patient.id == apt.patient_id
        ).first()

        try:
            doctor_name = apt.doctor.name
        except Exception:
            doctor_name = "your doctor"

        try:
            await bot.send_message(
                chat_id=patient.telegram_id,
                text=(
                    f"⏰ *Reminder!*\n\n"
                    f"You have an appointment in *2 hours*.\n\n"
                    f"📅 {apt.appointment_time.strftime('%d %b %Y, %I:%M %p')}\n"
                    f"👨‍⚕️ Dr. {doctor_name}\n\n"
                    f"Please be on time. See you soon! 🏥"
                ),
                parse_mode="Markdown"
            )
            apt.reminder_sent = True
            db.commit()
            print(f"Reminder sent to {patient.name}")
        except Exception as e:
            print(f"Failed to send reminder: {e}")

    db.close()

def start_scheduler(bot):
    scheduler.add_job(
        send_reminders,
        trigger="interval",
        minutes=1,
        args=[bot],
        id="reminder_job"
    )
    print("⏰ Reminder scheduler ready.")

def start_medication_scheduler(bot):
    from bot.notifications import send_medication_reminders
    scheduler.add_job(
        send_medication_reminders,
        trigger="interval",
        hours=1,
        args=[bot],
        id="med_reminder_job"
    )
    print("💊 Medication reminder scheduler started.")

async def send_pre_visit_questionnaires(bot):
    from bot.pre_visit import send_pre_visit_questionnaire
    db = SessionLocal()
    try:
        now = datetime.now()
        window = now + timedelta(hours=1)

        appointments = db.query(Appointment).filter(
            Appointment.status == "scheduled",
            Appointment.questionnaire_sent == False,
            Appointment.appointment_time >= now,
            Appointment.appointment_time <= window + timedelta(minutes=5)
        ).all()

        for apt in appointments:
            try:
                await send_pre_visit_questionnaire(bot, apt.id)
                apt.questionnaire_sent = True
                db.commit()
                print(f"📋 Pre-visit questionnaire sent for appointment {apt.id}")
            except Exception as e:
                print(f"Failed to send pre-visit questionnaire: {e}")
    finally:
        db.close()

def start_pre_visit_scheduler(bot):
    scheduler.add_job(
        send_pre_visit_questionnaires,
        trigger="interval",
        minutes=30,
        args=[bot],
        id="pre_visit_job"
    )
    print("📋 Pre-visit questionnaire scheduler ready.")