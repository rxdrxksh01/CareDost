"""
CareDost REST API — powers the React dashboard
All endpoints return JSON. Auth via Flask session cookies.
"""
from flask import Blueprint, request, jsonify, session, make_response
from db.database import SessionLocal
from db.models import Doctor, Patient, Appointment, VisitSummary, MedicationReminder, PreVisitForm, PatientMessage
from datetime import datetime, timedelta, timezone
from functools import wraps
import os, logging

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

api = Blueprint("api", __name__, url_prefix="/api")

# ── DEMO MODE: auto-login on every request ────────────────
def _ensure_session():
    """Auto-set doctor session so no login is needed for demos."""
    if not session.get("doctor_id"):
        db = SessionLocal()
        doctor = db.query(Doctor).first()
        if doctor:
            session["doctor_id"] = doctor.id
            session["doctor_name"] = doctor.name
        db.close()

def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        _ensure_session()
        return f(*args, **kwargs)
    return decorated

# ── auth (kept for compatibility, auto-passes now) ────────
@api.route("/login", methods=["POST"])
def api_login():
    _ensure_session()
    return jsonify({"ok": True, "doctor_name": session.get("doctor_name", "Doctor")})

@api.route("/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

@api.route("/me")
def api_me():
    _ensure_session()
    return jsonify({"logged_in": True, "doctor_name": session.get("doctor_name", "Doctor")})

# ── dashboard stats + appointments ────────────────────────
@api.route("/dashboard")
@api_login_required
def api_dashboard():
    db = SessionLocal()
    now = datetime.now(IST).replace(tzinfo=None)
    try:
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        today_apts = db.query(Appointment).filter(
            Appointment.appointment_time >= day_start,
            Appointment.appointment_time <= day_end,
            Appointment.status == "scheduled"
        ).order_by(Appointment.appointment_time).all()

        # Show all future scheduled patients (including later today) with no hard limit.
        upcoming_apts = db.query(Appointment).filter(
            Appointment.appointment_time >= now,
            Appointment.status == "scheduled"
        ).order_by(Appointment.appointment_time).all()

        recent_completed = db.query(Appointment).filter(
            Appointment.status == "completed"
        ).order_by(Appointment.appointment_time.desc()).limit(5).all()

        def serialize_apt(apt, show_date=False):
            fmt = "%d %b %Y, %I:%M %p" if show_date else "%I:%M %p"
            return {
                "id": apt.id,
                "time": apt.appointment_time.strftime(fmt),
                "raw_time": apt.appointment_time.isoformat(),
                "patient_name": apt.patient.name if apt.patient else "Unknown",
                "patient_phone": apt.patient.phone if apt.patient else "",
                "status": apt.status
            }

        total_patients = db.query(Patient).count()
        total_appointments = db.query(Appointment).count()
        completed = db.query(Appointment).filter(Appointment.status == "completed").count()
        cancelled = db.query(Appointment).filter(Appointment.status == "cancelled").count()
        active_reminders = db.query(MedicationReminder).filter(MedicationReminder.active == True).count()

        return jsonify({
            "stats": {
                "total_patients": total_patients,
                "total_appointments": total_appointments,
                "completed": completed,
                "cancelled": cancelled,
                "active_reminders": active_reminders,
                "today_count": len(today_apts)
            },
            "today": [serialize_apt(a) for a in today_apts],
            "upcoming": [serialize_apt(a, show_date=True) for a in upcoming_apts],
            "recent_completed": [serialize_apt(a, show_date=True) for a in recent_completed],
            "doctor_name": session.get("doctor_name")
        })
    finally:
        db.close()

# ── appointment detail ────────────────────────────────────
@api.route("/appointment/<int:apt_id>")
@api_login_required
def api_appointment_detail(apt_id):
    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt:
            return jsonify({"error": "Not found"}), 404

        summary = db.query(VisitSummary).filter(VisitSummary.appointment_id == apt_id).first()
        pre_visit = db.query(PreVisitForm).filter(PreVisitForm.appointment_id == apt_id).first()
        messages = db.query(PatientMessage).filter(
            PatientMessage.patient_id == apt.patient_id
        ).order_by(PatientMessage.created_at).all()

        return jsonify({
            "appointment": {
                "id": apt.id,
                "time": apt.appointment_time.strftime("%d %b %Y, %I:%M %p"),
                "raw_time": apt.appointment_time.isoformat(),
                "status": apt.status
            },
            "patient": {
                "name": apt.patient.name if apt.patient else "Unknown",
                "phone": apt.patient.phone if apt.patient else ""
            },
            "summary": {
                "notes": summary.notes,
                "medicines": summary.medicines,
                "follow_up_date": summary.follow_up_date.strftime("%Y-%m-%d") if summary.follow_up_date else ""
            } if summary else None,
            "pre_visit": {
                "main_problem": pre_visit.main_problem,
                "duration": pre_visit.duration,
                "severity": pre_visit.severity,
                "taking_medicine": pre_visit.taking_medicine,
                "extra_notes": pre_visit.extra_notes
            } if pre_visit else None,
            "messages": [{
                "id": m.id,
                "message": m.message,
                "file_path": f"/static/{m.file_path}" if m.file_path else None,
                "is_image": m.is_image,
                "direction": m.direction,
                "time": m.created_at.strftime("%I:%M %p") if m.created_at else ""
            } for m in messages]
        })
    finally:
        db.close()

# ── save visit notes ──────────────────────────────────────
@api.route("/appointment/<int:apt_id>/save", methods=["POST"])
@api_login_required
def api_save_notes(apt_id):
    data = request.json or {}
    notes = data.get("notes", "")
    medicines = data.get("medicines", "")
    follow_up = data.get("follow_up", "")

    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt:
            return jsonify({"error": "Not found"}), 404

        patient_id = apt.patient_id
        patient_name = apt.patient.name

        existing = db.query(VisitSummary).filter(VisitSummary.appointment_id == apt_id).first()
        follow_up_date = datetime.strptime(follow_up, "%Y-%m-%d") if follow_up else None

        if existing:
            existing.notes = notes
            existing.medicines = medicines
            existing.follow_up_date = follow_up_date
        else:
            new_summary = VisitSummary(
                appointment_id=apt_id, notes=notes,
                medicines=medicines, follow_up_date=follow_up_date
            )
            db.add(new_summary)

        # Auto revisit scheduling
        revisit_apt_id = None
        if follow_up_date:
            from datetime import time
            revisit_start = datetime.combine(follow_up_date.date(), time(0, 0))
            revisit_end = datetime.combine(follow_up_date.date(), time(23, 59))
            existing_revisit = db.query(Appointment).filter(
                Appointment.patient_id == patient_id,
                Appointment.appointment_time >= revisit_start,
                Appointment.appointment_time <= revisit_end,
                Appointment.status == "scheduled"
            ).first()
            if not existing_revisit:
                revisit_time = datetime.combine(follow_up_date.date(), time(10, 0))
                new_apt = Appointment(
                    doctor_id=session["doctor_id"], patient_id=patient_id,
                    appointment_time=revisit_time, status="scheduled"
                )
                db.add(new_apt)
                db.flush()
                try:
                    from bot.calendar_service import book_slot_on_calendar
                    doctor_name = db.query(Doctor).filter(Doctor.id == session["doctor_id"]).first().name
                    calendar_id = book_slot_on_calendar(revisit_time, patient_name, doctor_name)
                    if calendar_id:
                        new_apt.calendar_event_id = calendar_id
                except Exception as e:
                    logger.error(f"Calendar booking failed: {e}")
                revisit_apt_id = new_apt.id

        apt.status = "completed"

        # Medication Reminders
        if medicines:
            db.query(MedicationReminder).filter(
                MedicationReminder.patient_id == patient_id,
                MedicationReminder.active == True
            ).update({"active": False})
            for line in medicines.strip().split("\n"):
                line = line.strip()
                if not line: continue
                timings = []
                line_lower = line.lower()
                if any(w in line_lower for w in ["morning", "subah", "am"]): timings.append("morning")
                if any(w in line_lower for w in ["afternoon", "dopahar", "noon"]): timings.append("afternoon")
                if any(w in line_lower for w in ["evening", "shaam", "pm"]): timings.append("evening")
                if any(w in line_lower for w in ["night", "raat", "bedtime"]): timings.append("night")
                if not timings: timings = ["morning", "night"]
                for timing in timings:
                    reminder = MedicationReminder(
                        patient_id=patient_id, medicine_name=line,
                        timing=timing, start_date=datetime.now(),
                        end_date=datetime.now() + timedelta(days=7), active=True
                    )
                    db.add(reminder)

        db.commit()

        # Telegram notifications
        import asyncio
        from bot.notifications import notify_patient_visit_complete, notify_patient_revisit
        from main import get_bot
        try:
            bot = get_bot()
            asyncio.run(notify_patient_visit_complete(bot, apt_id))
            if revisit_apt_id:
                asyncio.run(notify_patient_revisit(bot, revisit_apt_id))
        except Exception as e:
            logger.error(f"Notification error: {e}")

        return jsonify({"ok": True, "revisit_scheduled": bool(revisit_apt_id)})
    except Exception as e:
        db.rollback()
        logger.error(f"Save notes error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ── cancel appointment ────────────────────────────────────
@api.route("/appointment/<int:apt_id>/cancel", methods=["POST"])
@api_login_required
def api_cancel_appointment(apt_id):
    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt:
            return jsonify({"error": "Not found"}), 404
        patient_tid = apt.patient.telegram_id
        apt_time = apt.appointment_time
        doctor_name = apt.doctor.name
        apt.status = "cancelled"
        if apt.calendar_event_id:
            from bot.calendar_service import delete_event_from_calendar
            delete_event_from_calendar(apt.calendar_event_id)
        db.commit()
        import asyncio
        from bot.notifications import notify_patient_cancellation
        from main import get_bot
        try:
            bot = get_bot()
            asyncio.run(notify_patient_cancellation(bot, patient_tid, apt_time, doctor_name))
        except Exception as e:
            logger.error(f"Cancel notify error: {e}")
        return jsonify({"ok": True})
    finally:
        db.close()

# ── send message ──────────────────────────────────────────
@api.route("/appointment/<int:apt_id>/message", methods=["POST"])
@api_login_required
def api_send_message(apt_id):
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400
    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt:
            return jsonify({"error": "Not found"}), 404
        patient_tid = apt.patient.telegram_id
        doctor_name = apt.doctor.name
        import asyncio
        from bot.notifications import send_direct_message
        from main import get_bot
        try:
            bot = get_bot()
            asyncio.run(send_direct_message(bot, patient_tid, message, doctor_name))
        except Exception as e:
            logger.error(f"Message error: {e}")
        return jsonify({"ok": True})
    finally:
        db.close()

# ── broadcast ─────────────────────────────────────────────
@api.route("/broadcast", methods=["POST"])
@api_login_required
def api_broadcast():
    data = request.json or {}
    message = data.get("message", "").strip()
    target_date_str = data.get("target_date", "")
    is_cancellation = data.get("is_cancellation", False)
    if not message or not target_date_str:
        return jsonify({"error": "Missing data"}), 400
    db = SessionLocal()
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        day_start = target_date.replace(hour=0, minute=0, second=0)
        day_end = target_date.replace(hour=23, minute=59, second=59)
        target_apts = db.query(Appointment).filter(
            Appointment.appointment_time >= day_start,
            Appointment.appointment_time <= day_end,
            Appointment.status == "scheduled"
        ).all()
        telegram_ids = list(set([apt.patient.telegram_id for apt in target_apts if apt.patient.telegram_id]))
        affected = len(telegram_ids)
        if is_cancellation:
            for apt in target_apts:
                apt.status = "cancelled"
                if apt.calendar_event_id:
                    from bot.calendar_service import delete_event_from_calendar
                    delete_event_from_calendar(apt.calendar_event_id)
            db.commit()
        if telegram_ids:
            import asyncio
            from bot.notifications import send_broadcast_message
            from main import get_bot
            try:
                bot = get_bot()
                asyncio.run(send_broadcast_message(bot, telegram_ids, message, is_cancellation))
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
        return jsonify({"ok": True, "affected": affected})
    finally:
        db.close()

# ── AI expand notes ───────────────────────────────────────
@api.route("/expand_notes", methods=["POST"])
@api_login_required
def api_expand_notes():
    data = request.json or {}
    shorthand = data.get("text", "").strip()
    if not shorthand:
        return jsonify({"expanded": ""})
    from groq import Groq
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a clinical AI assistant. Your task is to expand medical shorthand into professional paragraphs. RULES: 1. Keep it very brief (strictly 3-4 lines max). 2. DO NOT suggest, guess, or name any diseases or infections unless the doctor specifically provides them. 3. Only expand the shorthand provided into clear language. 4. Use a professional and sympathetic tone."},
                {"role": "user", "content": f"Expand this shorthand: {shorthand}"}
            ],
            temperature=0.7, max_tokens=500
        )
        return jsonify({"expanded": completion.choices[0].message.content})
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return jsonify({"expanded": shorthand, "error": str(e)})

# ── patients list ─────────────────────────────────────────
@api.route("/patients")
@api_login_required
def api_patients():
    db = SessionLocal()
    try:
        patients = db.query(Patient).all()
        result = []
        for p in patients:
            apt_count = db.query(Appointment).filter(Appointment.patient_id == p.id).count()
            last_apt = db.query(Appointment).filter(
                Appointment.patient_id == p.id
            ).order_by(Appointment.appointment_time.desc()).first()
            result.append({
                "id": p.id,
                "name": p.name,
                "phone": p.phone,
                "total_appointments": apt_count,
                "last_visit": last_apt.appointment_time.strftime("%d %b %Y") if last_apt else "Never"
            })
        return jsonify({"patients": result})
    finally:
        db.close()
