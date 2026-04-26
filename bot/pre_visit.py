import logging
from telegram import Update
from telegram.ext import ContextTypes
from db.database import SessionLocal
from db.models import Appointment, Patient, PreVisitForm
from bot.keyboards import (
    pre_visit_problem_kb, pre_visit_duration_kb,
    pre_visit_severity_kb, pre_visit_medicine_kb,
    pre_visit_skip_kb, pre_visit_review_kb
)

logger = logging.getLogger(__name__)


def save_previsit_draft(apt_id, **fields):
    """Persist partial questionnaire answers to avoid session-loss issues."""
    db = SessionLocal()
    try:
        form = db.query(PreVisitForm).filter(PreVisitForm.appointment_id == apt_id).first()
        if not form:
            form = PreVisitForm(appointment_id=apt_id)
            db.add(form)
        for key, val in fields.items():
            setattr(form, key, val)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed saving pre-visit draft for {apt_id}: {e}")
    finally:
        db.close()

# ── send initial questionnaire message ────────────────────
async def send_pre_visit_questionnaire(bot, appointment_id):
    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not apt:
            return

        patient = db.query(Patient).filter(Patient.id == apt.patient_id).first()
        if not patient:
            return

        await bot.send_message(
            chat_id=patient.telegram_id,
            text=(
                "Pre-Visit Questionnaire\n\n"
                f"Your appointment is coming up at "
                f"{apt.appointment_time.strftime('%I:%M %p')}.\n\n"
                "Please answer a few quick questions so the doctor "
                "can prepare for your visit.\n\n"
                "What's your main problem?"
            ),
            reply_markup=pre_visit_problem_kb(appointment_id)
        )
        logger.info(f"Pre-visit questionnaire sent for appointment {appointment_id}")
    except Exception as e:
        logger.error(f"Failed to send pre-visit questionnaire: {e}")
    finally:
        db.close()

# ── helper: extract apt_id and answer from callback_data ──
def parse_pv_callback(data, prefix):
    rest = data[len(prefix):]
    parts = rest.split("_", 1)
    apt_id = int(parts[0])
    answer = parts[1] if len(parts) > 1 else ""
    return apt_id, answer

def generate_review_text(apt_id, context):
    prob = context.user_data.get(f"pv_{apt_id}_problem", "")
    dur = context.user_data.get(f"pv_{apt_id}_duration", "")
    sev = context.user_data.get(f"pv_{apt_id}_severity", "")
    med = context.user_data.get(f"pv_{apt_id}_medicine", "")
    notes = context.user_data.get(f"pv_{apt_id}_notes", "")

    # Fallback to persisted draft if process restarted mid-questionnaire.
    if not all([prob, dur, sev, med]):
        db = SessionLocal()
        try:
            form = db.query(PreVisitForm).filter(PreVisitForm.appointment_id == apt_id).first()
            if form:
                prob = prob or (form.main_problem or "")
                dur = dur or (form.duration or "")
                sev = sev or (form.severity or "")
                med = med or (form.taking_medicine or "")
                notes = notes or (form.extra_notes or "")
        finally:
            db.close()
    
    text = "Please review your answers before submitting:\n\n"
    text += f"Problem: {prob}\n"
    text += f"Duration: {dur}\n"
    text += f"Severity: {sev}\n"
    text += f"Taking Medicine: {med}\n"
    text += f"Extra Notes: {notes if notes else 'None'}\n"
    return text

# ── handle 'Type my own answer' button ───────────────────
async def pv_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    
    try:
        apt_id, field = parse_pv_callback(query.data, "pv_type_")
        context.user_data["pv_typing_for_apt"] = apt_id
        context.user_data["pv_typing_field"] = field
        
        await query.edit_message_text("Please type your answer:")
    except Exception as e:
        logger.error(f"Error in pv_type_callback: {e}")

# ── Q1: main problem → ask duration ──────────────────────
async def pv_problem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        apt_id, answer = parse_pv_callback(query.data, "pv_prob_")
        context.user_data[f"pv_{apt_id}_problem"] = answer
        save_previsit_draft(apt_id, main_problem=answer)

        await query.edit_message_text(
            f"Main problem: {answer}\n\n"
            "How long have you had this?",
            reply_markup=pre_visit_duration_kb(apt_id)
        )
    except Exception as e:
        logger.error(f"Error in pv_problem_callback: {e}")

# ── Q2: duration → ask severity ──────────────────────────
async def pv_duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        apt_id, answer = parse_pv_callback(query.data, "pv_dur_")
        context.user_data[f"pv_{apt_id}_duration"] = answer
        save_previsit_draft(apt_id, duration=answer)

        await query.edit_message_text(
            f"Duration: {answer}\n\n"
            "How bad is it?",
            reply_markup=pre_visit_severity_kb(apt_id)
        )
    except Exception as e:
        logger.error(f"Error in pv_duration_callback: {e}")

# ── Q3: severity → ask medicine ──────────────────────────
async def pv_severity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        apt_id, answer = parse_pv_callback(query.data, "pv_sev_")
        context.user_data[f"pv_{apt_id}_severity"] = answer
        save_previsit_draft(apt_id, severity=answer)

        await query.edit_message_text(
            f"Severity: {answer}\n\n"
            "Are you taking any medicine already?",
            reply_markup=pre_visit_medicine_kb(apt_id)
        )
    except Exception as e:
        logger.error(f"Error in pv_severity_callback: {e}")

# ── Q4: medicine → ask extra notes ───────────────────────
async def pv_medicine_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        apt_id, answer = parse_pv_callback(query.data, "pv_med_")
        context.user_data[f"pv_{apt_id}_medicine"] = answer
        save_previsit_draft(apt_id, taking_medicine=answer)

        # Store apt_id so the free-text handler knows which appointment it's collecting notes for
        context.user_data["pv_typing_for_apt"] = apt_id
        context.user_data["pv_typing_field"] = "notes"

        await query.edit_message_text(
            f"Taking medicine: {answer}\n\n"
            "Anything else you want to tell the doctor?\n\n"
            "Type your message below, or tap Skip.",
            reply_markup=pre_visit_skip_kb(apt_id)
        )
    except Exception as e:
        logger.error(f"Error in pv_medicine_callback: {e}")

# ── Q5 (skip button): goto review ─────────────────────────
async def pv_skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    try:
        rest = query.data[len("pv_skip_"):]
        apt_id = int(rest)
        context.user_data.pop("pv_typing_for_apt", None)
        context.user_data.pop("pv_typing_field", None)
        context.user_data[f"pv_{apt_id}_notes"] = "Skipped"
        save_previsit_draft(apt_id, extra_notes="Skipped")

        review_text = generate_review_text(apt_id, context)
        await query.edit_message_text(
            review_text,
            reply_markup=pre_visit_review_kb(apt_id)
        )
    except Exception as e:
        logger.error(f"Error in pv_skip_callback: {e}")

# ── Handle Free Text ──────────────────────────────────────
async def pv_free_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apt_id = context.user_data.get("pv_typing_for_apt")
    field = context.user_data.get("pv_typing_field")
    
    if not apt_id or not field:
        # We also have ask_name and ask_phone handlers, so if we aren't in PV mode, ignore
        return

    answer = update.message.text.strip()
    
    if field == "notes":
        context.user_data.pop("pv_typing_for_apt", None)
        context.user_data.pop("pv_typing_field", None)
        context.user_data[f"pv_{apt_id}_notes"] = answer
        save_previsit_draft(apt_id, extra_notes=answer)

        review_text = generate_review_text(apt_id, context)
        await update.message.reply_text(
            review_text,
            reply_markup=pre_visit_review_kb(apt_id)
        )
    
    elif field == "problem":
        context.user_data[f"pv_{apt_id}_problem"] = answer
        save_previsit_draft(apt_id, main_problem=answer)
        context.user_data.pop("pv_typing_field", None) # clear field but keep going
        
        await update.message.reply_text(
            f"Main problem: {answer}\n\n"
            "How long have you had this?",
            reply_markup=pre_visit_duration_kb(apt_id)
        )
        
    elif field == "duration":
        context.user_data[f"pv_{apt_id}_duration"] = answer
        save_previsit_draft(apt_id, duration=answer)
        context.user_data.pop("pv_typing_field", None)
        
        await update.message.reply_text(
            f"Duration: {answer}\n\n"
            "How bad is it?",
            reply_markup=pre_visit_severity_kb(apt_id)
        )
        
    elif field == "severity":
        context.user_data[f"pv_{apt_id}_severity"] = answer
        save_previsit_draft(apt_id, severity=answer)
        context.user_data.pop("pv_typing_field", None)
        
        await update.message.reply_text(
            f"Severity: {answer}\n\n"
            "Are you taking any medicine already?",
            reply_markup=pre_visit_medicine_kb(apt_id)
        )
        
    elif field == "medicine":
        context.user_data[f"pv_{apt_id}_medicine"] = answer
        save_previsit_draft(apt_id, taking_medicine=answer)
        context.user_data["pv_typing_field"] = "notes" # next field is notes
        
        await update.message.reply_text(
            f"Taking medicine: {answer}\n\n"
            "Anything else you want to tell the doctor?\n\n"
            "Type your message below, or tap Skip.",
            reply_markup=pre_visit_skip_kb(apt_id)
        )

# ── Submit / Redo callbacks ───────────────────────────────
async def pv_submit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
        
    try:
        rest = query.data[len("pv_submit_"):]
        apt_id = int(rest)
        
        db = SessionLocal()
        try:
            existing = db.query(PreVisitForm).filter(PreVisitForm.appointment_id == apt_id).first()
            apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
            if not apt:
                await query.edit_message_text(
                    "This form is no longer active. Please book again with /start."
                )
                return
            
            problem_val = context.user_data.get(f"pv_{apt_id}_problem", "")
            if not problem_val and existing:
                problem_val = existing.main_problem or ""
            if not problem_val:
                # Keep flow resilient even if context was lost.
                problem_val = "Not provided"

            duration_val = context.user_data.get(f"pv_{apt_id}_duration", "") or (existing.duration if existing else "")
            severity_val = context.user_data.get(f"pv_{apt_id}_severity", "") or (existing.severity if existing else "")
            medicine_val = context.user_data.get(f"pv_{apt_id}_medicine", "") or (existing.taking_medicine if existing else "")
            notes_val = context.user_data.get(f"pv_{apt_id}_notes", "") or (existing.extra_notes if existing else "")
            form = existing or PreVisitForm(appointment_id=apt_id)
            form.main_problem = problem_val
            form.duration = duration_val
            form.severity = severity_val
            form.taking_medicine = medicine_val
            form.extra_notes = notes_val

            db.add(form)
            db.commit()
            
            # Clean up user_data
            for key in [f"pv_{apt_id}_problem", f"pv_{apt_id}_duration", f"pv_{apt_id}_severity", f"pv_{apt_id}_medicine", f"pv_{apt_id}_notes"]:
                context.user_data.pop(key, None)
            context.user_data.pop("pv_typing_for_apt", None)
            context.user_data.pop("pv_typing_field", None)
            
            await query.edit_message_text(
                "Pre-visit form submitted successfully.\n\n"
                "Thank you. The doctor will review your responses before your appointment."
            )
            logger.info(f"Pre-visit form saved for appointment {apt_id}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in pv_submit_callback: {e}")
        try:
            await query.edit_message_text(
                "Couldn't submit right now. Tap Submit again in a few seconds."
            )
        except Exception:
            pass

async def pv_redo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
        
    try:
        rest = query.data[len("pv_redo_"):]
        apt_id = int(rest)
        
        # Clear data
        for key in [f"pv_{apt_id}_problem", f"pv_{apt_id}_duration", f"pv_{apt_id}_severity", f"pv_{apt_id}_medicine", f"pv_{apt_id}_notes"]:
            context.user_data.pop(key, None)
        context.user_data.pop("pv_typing_for_apt", None)
        context.user_data.pop("pv_typing_field", None)
        
        await query.edit_message_text(
            "Let's start over.\n\n"
            "What's your main problem?",
            reply_markup=pre_visit_problem_kb(apt_id)
        )
    except Exception as e:
        logger.error(f"Error in pv_redo_callback: {e}")
