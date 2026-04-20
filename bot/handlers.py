from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.keyboards import main_menu, time_slots, confirm_booking
from db.database import SessionLocal
from db.models import Patient, Doctor, Appointment
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ASK_NAME, ASK_PHONE, PICK_SLOT, CONFIRM_SLOT = range(4)

# ── safe helpers ──────────────────────────────────────────
async def safe_answer(query):
    try:
        await query.answer()
    except Exception:
        pass

def get_patient(db, telegram_id):
    try:
        return db.query(Patient).filter(
            Patient.telegram_id == str(telegram_id)
        ).first()
    except Exception as e:
        logger.error(f"Error fetching patient: {e}")
        return None

def get_doctor(db):
    try:
        return db.query(Doctor).first()
    except Exception as e:
        logger.error(f"Error fetching doctor: {e}")
        return None

# ── /start ────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = SessionLocal()

    try:
        # Clear leftover pre-visit state
        context.user_data.pop("pv_typing_for_apt", None)
        context.user_data.pop("pv_typing_field", None)
        
        patient = get_patient(db, user.id)

        if not patient:
            await update.message.reply_text(
                "👋 Welcome to *CareDost*!\n\n"
                "I'm your personal clinic assistant.\n\n"
                "First, what's your full name?",
                parse_mode="Markdown"
            )
            return ASK_NAME

        await update.message.reply_text(
            f"👋 Welcome back, *{patient.name}*!\n\nHow can I help you today?",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text(
            "⚠️ Something went wrong. Please try again."
        )
        return ConversationHandler.END
    finally:
        db.close()

# ── collect name ──────────────────────────────────────────
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name = update.message.text.strip()
        if len(name) < 2:
            await update.message.reply_text(
                "Please enter a valid name."
            )
            return ASK_NAME

        context.user_data["name"] = name
        await update.message.reply_text(
            f"Nice to meet you, *{name}*! 😊\n\nWhat's your phone number?",
            parse_mode="Markdown"
        )
        return ASK_PHONE

    except Exception as e:
        logger.error(f"Error in ask_name: {e}")
        await update.message.reply_text("⚠️ Something went wrong. Send /start to try again.")
        return ConversationHandler.END

# ── collect phone ─────────────────────────────────────────
async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = SessionLocal()

    try:
        phone = update.message.text.strip()
        if len(phone) < 7:
            await update.message.reply_text(
                "Please enter a valid phone number."
            )
            return ASK_PHONE

        # check if already registered
        existing = get_patient(db, user.id)
        if existing:
            await update.message.reply_text(
                "✅ You're already registered!\n\nHow can I help you today?",
                reply_markup=main_menu()
            )
            return ConversationHandler.END

        patient = Patient(
            telegram_id=str(user.id),
            name=context.user_data.get("name", "Patient"),
            phone=phone
        )
        db.add(patient)
        db.commit()

        await update.message.reply_text(
            "✅ You're registered!\n\nHow can I help you today?",
            reply_markup=main_menu()
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in ask_phone: {e}")
        db.rollback()
        await update.message.reply_text("⚠️ Registration failed. Send /start to try again.")
        return ConversationHandler.END
    finally:
        db.close()

# ── main menu callback ────────────────────────────────────
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        if query.data == "book":
            slots = get_available_slots()
            if not slots:
                await query.edit_message_text(
                    "😔 No slots available right now.\n\nPlease try again later."
                )
                return

            await query.edit_message_text(
                "📅 *Available slots:*\n\nPick a time that works for you:",
                parse_mode="Markdown",
                reply_markup=time_slots(slots)
            )

        elif query.data == "my_appointments":
            user = query.from_user
            db = SessionLocal()

            try:
                patient = get_patient(db, user.id)
                if not patient:
                    await query.edit_message_text(
                        "No account found. Send /start to register."
                    )
                    return

                appointments = db.query(Appointment).filter(
                    Appointment.patient_id == patient.id,
                    Appointment.status == "scheduled",
                    Appointment.appointment_time >= datetime.now()
                ).order_by(Appointment.appointment_time).all()

                if not appointments:
                    await query.edit_message_text(
                        "📋 You have no upcoming appointments.\n\n"
                        "Send /start and book one!"
                    )
                    return

                text = "📋 *Your Upcoming Appointments:*\n\n"
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = []

                for i, apt in enumerate(appointments, 1):
                    text += (
                        f"{i}. 📅 {apt.appointment_time.strftime('%d %b %Y')}\n"
                        f"   🕐 {apt.appointment_time.strftime('%I:%M %p')}\n"
                        f"   🔔 Reminder: {'Sent ✅' if apt.reminder_sent else 'Pending ⏳'}\n\n"
                    )
                    keyboard.append([InlineKeyboardButton(f"❌ Cancel Session #{i}", callback_data=f"cancel_apt_{apt.id}")])

                keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="start")])

                await query.edit_message_text(
                    text, 
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            finally:
                db.close()

        elif query.data == "help":
            await query.edit_message_text(
                "❓ *Help*\n\n"
                "• Use /start to go back to main menu\n"
                "• Book an appointment and I'll remind you 2 hours before\n"
                "• Use /cancel to cancel current action\n"
                "• Contact clinic: +91-XXXXXXXXXX",
                parse_mode="Markdown"
            )

        elif query.data == "cancel":
            await query.edit_message_text(
                "Cancelled. Send /start to start again."
            )

        elif query.data.startswith("cancel_apt_"):
            apt_id = int(query.data.replace("cancel_apt_", ""))
            db = SessionLocal()
            try:
                apt_to_cancel = db.query(Appointment).filter(Appointment.id == apt_id).first()
                if apt_to_cancel:
                    apt_to_cancel.status = "cancelled"
                    if apt_to_cancel.calendar_event_id:
                        from bot.calendar_service import delete_event_from_calendar
                        delete_event_from_calendar(apt_to_cancel.calendar_event_id)
                    db.commit()
                    await query.edit_message_text(
                        " Appointment has been successfully cancelled and removed from the calendar.\n\n"
                        "Send /start to go back to the menu."
                    )
                else:
                    await query.edit_message_text(" Appointment not found.")
            finally:
                db.close()

    except Exception as e:
        logger.error(f"Error in menu_callback: {e}")
        try:
            await query.edit_message_text(
                " Something went wrong. Send /start to try again."
            )
        except Exception:
            pass

# ── slot selection ────────────────────────────────────────
async def slot_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        slot_id = query.data.replace("slot_", "")
        slots = get_available_slots()
        selected = next((s for s in slots if str(s["id"]) == slot_id), None)

        if not selected:
            await query.edit_message_text(
                "⚠️ Slot no longer available. Send /start to see fresh slots."
            )
            return

        context.user_data["selected_slot"] = {
            "id": selected["id"],
            "time": selected["time"],
            "datetime_str": selected["datetime"].isoformat()
        }

        await query.edit_message_text(
            f"You selected *{selected['time']}*\n\nConfirm your booking?",
            parse_mode="Markdown",
            reply_markup=confirm_booking(slot_id)
        )

    except Exception as e:
        logger.error(f"Error in slot_selected: {e}")
        await query.edit_message_text(
            " Something went wrong. Send /start to try again."
        )

# ── confirm booking ───────────────────────────────────────
async def confirm_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    db = SessionLocal()

    try:
        user = update.effective_user
        patient = get_patient(db, user.id)

        if not patient:
            await query.edit_message_text(
                " Account not found. Send /start to register first."
            )
            return

        doctor = get_doctor(db)
        if not doctor:
            await query.edit_message_text(
                " No doctor available right now. Please contact the clinic directly."
            )
            return

        selected = context.user_data.get("selected_slot")
        if not selected:
            await query.edit_message_text(
                "Session expired. Please send /start and book again."
            )
            return

        # parse datetime from string so it survives bot restarts
        apt_time = datetime.fromisoformat(selected["datetime_str"])
        
        if apt_time <= datetime.now():
            await query.edit_message_text(
                "⚠️ This slot is now in the past. Please send /start to pick a fresh time."
            )
            return

        # check slot not already taken
        conflict = db.query(Appointment).filter(
            Appointment.appointment_time == apt_time,
            Appointment.status == "scheduled"
        ).first()

        if conflict:
            await query.edit_message_text(
                "⚠️ Sorry, this slot was just taken. Send /start to pick another."
            )
            return

        doctor_name = doctor.name
        doctor_id = doctor.id

        appointment = Appointment(
            doctor_id=doctor_id,
            patient_id=patient.id,
            appointment_time=apt_time,
            status="scheduled"
        )
        db.add(appointment)
        db.commit()
        try:
            from bot.calendar_service import book_slot_on_calendar
            event_id = book_slot_on_calendar(apt_time, patient.name, doctor_name)
            if event_id:
                appointment.calendar_event_id = event_id
                db.commit()
        except Exception as e:
            logger.error(f"Calendar booking failed: {e}")

        await query.edit_message_text(
            f"✅ *Booking Confirmed!*\n\n"
            f"📅 {selected['time']}\n"
            f"👨‍⚕️ Doctor: {doctor_name}\n\n"
            f"I'll remind you 2 hours before. 🔔",
            parse_mode="Markdown"
        )
        # Clear selected slot so they can't double-confirm
        context.user_data.pop("selected_slot", None)

        # send pre-visit questionnaire immediately
        try:
            from bot.pre_visit import send_pre_visit_questionnaire
            apt_id = appointment.id
            appointment.questionnaire_sent = True
            db.commit()
            await send_pre_visit_questionnaire(context.bot, apt_id)
        except Exception as e:
            logger.error(f"Failed to send pre-visit questionnaire: {e}")

    except Exception as e:
        logger.error(f"Error in confirm_slot: {e}")
        db.rollback()
        try:
            await query.edit_message_text(
                "⚠️ Booking failed. Send /start and try again."
            )
        except Exception:
            pass
    finally:
        db.close()

# ── helper: generate slots ────────────────────────────────
def get_available_slots():
    try:
        from bot.calendar_service import get_available_slots_from_calendar
        from db.database import SessionLocal
        from db.models import Appointment

        calendar_slots = get_available_slots_from_calendar()

        # also filter out slots already booked in our DB
        db = SessionLocal()
        try:
            booked_times = [
                a.appointment_time for a in db.query(Appointment).filter(
                    Appointment.status == "scheduled"
                ).all()
            ]
        finally:
            db.close()

        filtered = []
        for slot in calendar_slots:
            if slot["datetime"] not in booked_times:
                filtered.append(slot)

        return filtered

    except Exception as e:
        logger.error(f"Calendar error, falling back to default slots: {e}")
        return get_default_slots()

def get_default_slots():
    slots = []
    now = datetime.now()
    db = SessionLocal()

    try:
        booked_times = [
            a.appointment_time for a in db.query(Appointment).filter(
                Appointment.status == "scheduled"
            ).all()
        ]
    except Exception:
        booked_times = []
    finally:
        db.close()

    for day_offset in range(2):
        base = (now + timedelta(days=day_offset)).replace(
            minute=0, second=0, microsecond=0
        )
        for hour in range(16, 19):
            slot_time = base.replace(hour=hour)
            if slot_time <= now:
                continue
            if slot_time in booked_times:
                continue
            slots.append({
                "id": len(slots) + 1,
                "time": slot_time.strftime("%d %b, %I:%M %p"),
                "datetime": slot_time
            })
            if len(slots) >= 5:
                break
        if len(slots) >= 5:
            break

    return slots

# ── cancel ────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Cancelled. Send /start to start again."
    )
    return ConversationHandler.END

async def patient_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This handler catches any text not caught by Pre-Visit or ConversationHandler
    if not update.message or not update.message.text:
        return

    # Check if we are in Pre-Visit mode - if so, delegate to the pre-visit handler
    if context.user_data.get("pv_typing_for_apt"):
        from bot.pre_visit import pv_free_text_handler
        return await pv_free_text_handler(update, context)

    text = update.message.text.strip()
    telegram_id = str(update.effective_user.id)
    
    from db.database import SessionLocal
    from db.models import Patient
    
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.telegram_id == telegram_id).first()
        
        if patient:
            # Use helper to check credits
            if not await check_patient_credits(update, patient, db):
                return

            from db.models import PatientMessage
            # Save the message
            new_msg = PatientMessage(
                patient_id=patient.id,
                message=text,
                direction="from_patient"
            )
            db.add(new_msg)
            db.commit()
            
            await update.message.reply_text("Thanks! I've forwarded your message to Dr. Sharma. 🙏")
        else:
            # If unknown user, just give start prompt
            await update.message.reply_text("Welcome to CareDost! Please type /start to book an appointment.")
            
    except Exception as e:
        logger.error(f"Error in patient_reply_handler: {e}")
    finally:
        db.close()

async def check_patient_credits(update: Update, patient, db):
    """Helper to check and deduct credits. Returns True if allowed, False otherwise."""
    if patient.reply_credits > 0:
        patient.reply_credits -= 1
        return True
    elif patient.initiation_credits > 0:
        patient.initiation_credits -= 1
        return True
    else:
        await update.message.reply_text(
            "You've reached your free message/attachment limit. 📩\n\n"
            "The doctor will see your previous messages during your visit. "
            "You can still book new slots if needed!"
        )
        return False

async def patient_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles photos and documents sent by the patient."""
    if not update.message:
        return
        
    # Ignore if in Pre-Visit questionnaire typing mode
    if context.user_data.get("pv_typing_for_apt"):
        return

    telegram_id = str(update.effective_user.id)
    from db.database import SessionLocal
    from db.models import Patient, PatientMessage
    import os
    import uuid

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.telegram_id == telegram_id).first()
        if not patient: return

        if not await check_patient_credits(update, patient, db):
            return

        file_id = None
        is_image = False
        extension = ""

        if update.message.photo:
            file_id = update.message.photo[-1].file_id  # Best quality
            is_image = True
            extension = ".jpg"
        elif update.message.document:
            file_id = update.message.document.file_id
            # Check mime type for image
            mime = update.message.document.mime_type or ""
            is_image = mime.startswith("image/")
            # keep original extension
            orig_name = update.message.document.file_name or "file"
            extension = os.path.splitext(orig_name)[1] or ".doc"
            
        if not file_id:
            return

        # Prepare folder
        static_dir = "dashboard/static/uploads"
        if not os.path.exists(static_dir):
            os.makedirs(static_dir, exist_ok=True)

        new_name = f"{uuid.uuid4()}{extension}"
        file_path = f"uploads/{new_name}"
        full_path = os.path.join(static_dir, new_name)

        # Download
        tg_file = await context.bot.get_file(file_id)
        await tg_file.download_to_drive(full_path)

        # Save to DB
        caption = update.message.caption or ""
        new_msg = PatientMessage(
            patient_id=patient.id,
            message=caption,
            file_path=file_path,
            is_image=is_image,
            direction="from_patient"
        )
        db.add(new_msg)
        db.commit()

        await update.message.reply_text("📎 I've shared your file with the doctor. They'll review it during your visit!")
    except Exception as e:
        import logging
        logging.error(f"Media handler error: {e}")
        await update.message.reply_text("Sorry, I had trouble saving that file. Please try again.")
    finally:
        db.close()