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

async def notify_patient_cancellation(bot, telegram_id: str, apt_time: datetime, doctor_name: str):
    try:
        msg = (
            f"⚠️ *Appointment Cancelled*\n\n"
            f"Your appointment with Dr. {doctor_name} scheduled for "
            f"*{apt_time.strftime('%d %b %Y, %I:%M %p')}* has been cancelled by the clinic.\n\n"
            f"Please type /start to book a new slot or contact the clinic directly."
        )
        await bot.send_message(
            chat_id=telegram_id,
            text=msg,
            parse_mode="Markdown"
        )
        logger.info(f"Cancellation notice sent to {telegram_id}")
    except Exception as e:
        logger.error(f"Failed to send cancellation notice: {e}")

async def send_direct_message(bot, telegram_id: str, message: str, doctor_name: str):
    from db.database import SessionLocal
    from db.models import Patient, PatientMessage
    
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.telegram_id == telegram_id).first()
        if patient:
            # Save to DB first
            new_msg = PatientMessage(
                patient_id=patient.id,
                message=message,
                direction="to_patient"
            )
            patient.reply_credits = 2  # Grant 2 replies per doctor message
            db.add(new_msg)
            db.commit()

        msg = f"👨‍⚕️ *Message from Dr. {doctor_name}:*\n\n{message}"
        await bot.send_message(
            chat_id=telegram_id,
            text=msg,
            parse_mode="Markdown"
        )
        logger.info(f"Direct message sent to {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send direct message to {telegram_id}: {e}")
        return False
    finally:
        db.close()

async def send_broadcast_message(bot, telegram_ids: list, message: str, is_cancellation: bool = False):
    success_count = 0
    msg = f"📢 *Clinic Announcement*\n\n{message}"
    
    reply_markup = None
    if is_cancellation:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("📅 Book New Slot", callback_data="book")
        ]])
    
    for tid in telegram_ids:
        try:
            await bot.send_message(
                chat_id=tid,
                text=msg,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {tid}: {e}")
            
    logger.info(f"Broadcast sent successfully to {success_count}/{len(telegram_ids)} patients.")
    return success_count

async def notify_patient_revisit(bot, apt_id: int):
    from db.database import SessionLocal
    from db.models import Appointment
    
    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt:
            return
            
        telegram_id = apt.patient.telegram_id
        if not telegram_id:
            return

        time_str = apt.appointment_time.strftime("%d %b, %I:%M %p")
        msg = (
            "🏥 *Follow-up Scheduled*\n\n"
            f"Dr. {apt.doctor.name} has scheduled a follow-up visit for you on:\n"
            f"📅 *{time_str}*\n\n"
            "We look forward to seeing you then!"
        )
        
        await bot.send_message(
            chat_id=telegram_id,
            text=msg,
            parse_mode="Markdown"
        )
        logger.info(f"Re-visit notification sent to {telegram_id}")
    except Exception as e:
        logger.error(f"Failed to send re-visit notification: {e}")
    finally:
        db.close()