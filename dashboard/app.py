from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import io
import os
from fpdf import FPDF
from db.database import SessionLocal
from db.models import Doctor, Patient, Appointment, VisitSummary, MedicationReminder, PreVisitForm, PatientMessage
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "caredost-secret-2026")

# ── auth decorator ────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("doctor_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ── login ─────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == os.getenv("DASHBOARD_USERNAME", "doctor") and password == os.getenv("DASHBOARD_PASSWORD", "caredost123"):
            db = SessionLocal()
            doctor = db.query(Doctor).first()
            session["doctor_id"] = doctor.id
            session["doctor_name"] = doctor.name
            db.close()
            return redirect(url_for("dashboard"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)

# ── logout ────────────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    db = SessionLocal()
    now = datetime.now()

    try:
        today_apts = db.query(Appointment).filter(
            Appointment.appointment_time >= now.replace(hour=0, minute=0, second=0),
            Appointment.appointment_time <= now.replace(hour=23, minute=59, second=59),
            Appointment.status == "scheduled"
        ).order_by(Appointment.appointment_time).all()

        upcoming_apts = db.query(Appointment).filter(
            Appointment.appointment_time > now.replace(hour=23, minute=59, second=59),
            Appointment.status == "scheduled"
        ).order_by(Appointment.appointment_time).limit(10).all()

        # load all data while session is open
        today = []
        for apt in today_apts:
            today.append({
                "id": apt.id,
                "time": apt.appointment_time.strftime("%I:%M %p"),
                "patient_name": apt.patient.name,
                "patient_phone": apt.patient.phone,
                "status": apt.status
            })

        upcoming = []
        for apt in upcoming_apts:
            upcoming.append({
                "id": apt.id,
                "time": apt.appointment_time.strftime("%d %b %Y, %I:%M %p"),
                "patient_name": apt.patient.name,
                "patient_phone": apt.patient.phone,
                "status": apt.status
            })

        total_patients = db.query(Patient).count()
        total_appointments = db.query(Appointment).count()
        completed = db.query(Appointment).filter(
            Appointment.status == "completed"
        ).count()

    finally:
        db.close()

    return render_template("dashboard.html",
        today=today,
        upcoming=upcoming,
        total_patients=total_patients,
        total_appointments=total_appointments,
        completed=completed,
        doctor_name=session.get("doctor_name")
    )

# ── visit summary ─────────────────────────────────────────
@app.route("/appointment/<int:apt_id>", methods=["GET", "POST"])
@login_required
def appointment_detail(apt_id):
    db = SessionLocal()

    try:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt:
            db.close()
            return redirect(url_for("dashboard"))

        patient_name = apt.patient.name
        patient_phone = apt.patient.phone
        patient_telegram_id = apt.patient.telegram_id
        patient_id = apt.patient_id
        apt_time = apt.appointment_time
        apt_status = apt.status

        summary = db.query(VisitSummary).filter(
            VisitSummary.appointment_id == apt_id
        ).first()

        summary_data = None
        # Fetch chat history
        chat_history = db.query(PatientMessage).filter(PatientMessage.patient_id == patient_id).order_by(PatientMessage.created_at).all()

        if summary:
            summary_data = {
                "notes": summary.notes,
                "medicines": summary.medicines,
                "follow_up_date": summary.follow_up_date
            }

        # fetch pre-visit form
        pre_visit = db.query(PreVisitForm).filter(
            PreVisitForm.appointment_id == apt_id
        ).first()

        pre_visit_data = None
        if pre_visit:
            pre_visit_data = {
                "main_problem": pre_visit.main_problem,
                "duration": pre_visit.duration,
                "severity": pre_visit.severity,
                "taking_medicine": pre_visit.taking_medicine,
                "extra_notes": pre_visit.extra_notes
            }

    finally:
        db.close()

    if request.method == "POST":
        notes = request.form.get("notes", "")
        medicines = request.form.get("medicines", "")
        follow_up = request.form.get("follow_up", "")

        db = SessionLocal()
        try:
            apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
            if not apt:
                db.close()
                return redirect(url_for("dashboard"))
                
            patient_id = apt.patient_id
            patient_name = apt.patient.name
            
            existing = db.query(VisitSummary).filter(
                VisitSummary.appointment_id == apt_id
            ).first()

            follow_up_date = datetime.strptime(follow_up, "%Y-%m-%d") if follow_up else None

            if existing:
                existing.notes = notes
                existing.medicines = medicines
                existing.follow_up_date = follow_up_date
            else:
                new_summary = VisitSummary(
                    appointment_id=apt_id,
                    notes=notes,
                    medicines=medicines,
                    follow_up_date=follow_up_date
                )
                db.add(new_summary)
            
            # --- PHASE 2: AUTOMATIC RE-VISIT ---
            if follow_up_date:
                # Check if a scheduled revisit already exists for this date to avoid duplicates
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
                    # Create new appointment at default 10:00 AM
                    revisit_time = datetime.combine(follow_up_date.date(), time(10, 0))
                    new_apt = Appointment(
                        doctor_id=session["doctor_id"],
                        patient_id=patient_id,
                        appointment_time=revisit_time,
                        status="scheduled"
                    )
                    db.add(new_apt)
                    db.flush() # get new_apt.id

                    # Sync to Calendar
                    from bot.calendar_service import book_slot_on_calendar
                    doctor_name = db.query(Doctor).filter(Doctor.id == session["doctor_id"]).first().name
                    calendar_id = book_slot_on_calendar(revisit_time, patient_name, doctor_name)
                    if calendar_id:
                        new_apt.calendar_event_id = calendar_id
                        
                    # Queue notification data
                    revisit_apt_id = new_apt.id
                else:
                    revisit_apt_id = None
            else:
                revisit_apt_id = None
            # -----------------------------------

            apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
            apt.status = "completed"

            # parse and save medication reminders
            if medicines:
                from datetime import timedelta
                # deactivate old reminders for this patient
                db.query(MedicationReminder).filter(
                    MedicationReminder.patient_id == patient_id,
                    MedicationReminder.active == True
                ).update({"active": False})

                # parse medicines — each line is one medicine
                for line in medicines.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue

                    # detect timing keywords
                    timings = []
                    line_lower = line.lower()
                    if any(w in line_lower for w in ["morning", "subah", "am"]):
                        timings.append("morning")
                    if any(w in line_lower for w in ["afternoon", "dopahar", "noon"]):
                        timings.append("afternoon")
                    if any(w in line_lower for w in ["evening", "shaam", "pm"]):
                        timings.append("evening")
                    if any(w in line_lower for w in ["night", "raat", "bedtime"]):
                        timings.append("night")
                    if not timings:
                        timings = ["morning", "night"]  # default twice daily

                    for timing in timings:
                        reminder = MedicationReminder(
                            patient_id=patient_id,
                            medicine_name=line,
                            timing=timing,
                            start_date=datetime.now(),
                            end_date=datetime.now() + timedelta(days=7),
                            active=True
                        )
                        db.add(reminder)

            db.commit()

            # store apt_id for async notification
            saved_apt_id = apt_id

        finally:
            db.close()

        # send telegram notification async
        import asyncio
        from bot.notifications import notify_patient_visit_complete
        from main import get_bot

        try:
            bot = get_bot()
            asyncio.run(notify_patient_visit_complete(bot, saved_apt_id))
            
            # Notify about revisit if scheduled
            if 'revisit_apt_id' in locals() and revisit_apt_id:
                from bot.notifications import notify_patient_revisit
                asyncio.run(notify_patient_revisit(bot, revisit_apt_id))
        except Exception as e:
            print(f"Notification error: {e}")

        return redirect(url_for("dashboard"))

    return render_template("appointment.html",
        apt={"id": apt_id, "time": apt_time, "status": apt_status},
        patient={"name": patient_name, "phone": patient_phone},
        summary=summary_data,
        pre_visit=pre_visit_data,
        messages=chat_history
    )

@app.route("/api/expand_notes", methods=["POST"])
@login_required
def expand_notes():
    data = request.json
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
            temperature=0.7,
            max_tokens=500
        )
        expanded = completion.choices[0].message.content
        return jsonify({"expanded": expanded})
    except Exception as e:
        print(f"Groq error: {e}")
        return jsonify({"expanded": shorthand, "error": str(e)})


@app.route("/appointment/<int:apt_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(apt_id):
    db = SessionLocal()
    patient_id = None
    apt_time = None
    doctor_name = None

    try:
        apt_to_cancel = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if apt_to_cancel:
            patient_id = apt_to_cancel.patient.telegram_id
            apt_time = apt_to_cancel.appointment_time
            doctor_name = apt_to_cancel.doctor.name
            
            apt_to_cancel.status = "cancelled"
            if apt_to_cancel.calendar_event_id:
                from bot.calendar_service import delete_event_from_calendar
                delete_event_from_calendar(apt_to_cancel.calendar_event_id)
            db.commit()
    finally:
        db.close()

    if patient_id and apt_time and doctor_name:
        import asyncio
        from bot.notifications import notify_patient_cancellation
        from main import get_bot
        try:
            bot = get_bot()
            asyncio.run(notify_patient_cancellation(bot, patient_id, apt_time, doctor_name))
        except Exception as e:
            print(f"Cancellation notification error: {e}")

    return redirect(url_for("dashboard"))
@app.route("/appointment/<int:apt_id>/message", methods=["POST"])
@login_required
def send_direct_message_route(apt_id):
    message = request.form.get("message", "").strip()
    if not message:
        return redirect(url_for("appointment_detail", apt_id=apt_id))
        
    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if apt:
            patient_id = apt.patient.telegram_id
            doctor_name = apt.doctor.name
            
            import asyncio
            from bot.notifications import send_direct_message
            from main import get_bot
            
            try:
                bot = get_bot()
                asyncio.run(send_direct_message(bot, patient_id, message, doctor_name))
            except Exception as e:
                print(f"Message send error: {e}")
    finally:
        db.close()
        
    return redirect(url_for("appointment_detail", apt_id=apt_id))

@app.route("/broadcast", methods=["POST"])
@login_required
def send_broadcast_route():
    message = request.form.get("message", "").strip()
    target_date_str = request.form.get("target_date")
    is_cancellation = request.form.get("is_cancellation") == "on"
    
    if not message or not target_date_str:
        return redirect(url_for("dashboard"))
        
    db = SessionLocal()
    try:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            target_date = datetime.now()
            
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        target_apts = db.query(Appointment).filter(
            Appointment.appointment_time >= day_start,
            Appointment.appointment_time <= day_end,
            Appointment.status == "scheduled"
        ).all()
        
        telegram_ids = []
        for apt in target_apts:
            if apt.patient.telegram_id and apt.patient.telegram_id not in telegram_ids:
                telegram_ids.append(apt.patient.telegram_id)
                
            if is_cancellation:
                apt.status = "cancelled"
                if apt.calendar_event_id:
                    from bot.calendar_service import delete_event_from_calendar
                    delete_event_from_calendar(apt.calendar_event_id)
        
        if is_cancellation:
            db.commit()
        
        if telegram_ids:
            import asyncio
            from bot.notifications import send_broadcast_message
            from main import get_bot
            
            try:
                bot = get_bot()
                asyncio.run(send_broadcast_message(bot, telegram_ids, message, is_cancellation))
            except Exception as e:
                print(f"Broadcast error: {e}")
    finally:
        db.close()
        
    return redirect(url_for("dashboard"))

@app.route("/appointment/<int:apt_id>/prescription")
@login_required
def download_prescription_route(apt_id):
    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt:
            return "Appointment not found", 404
        
        summary = db.query(VisitSummary).filter(VisitSummary.appointment_id == apt_id).first()
        if not summary:
            return "No visit notes found. Please save notes first.", 400

        # Generate PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(30, 41, 59) # Slate
        pdf.cell(0, 15, "CareDost Digital Clinic", 0, 1, "C")
        
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(100, 116, 139) # Light Slate
        pdf.cell(0, 5, "Professional Clinical Care — Anytime, Anywhere", 0, 1, "C")
        pdf.ln(10)
        
        # Horizontal Line
        pdf.set_draw_color(226, 232, 240)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
        # Patient Details Box
        pdf.set_fill_color(248, 250, 252)
        pdf.rect(10, pdf.get_y(), 190, 30, "F")
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(15, pdf.get_y() + 5)
        pdf.cell(90, 8, f"Patient: {apt.patient.name}")
        pdf.cell(90, 8, f"Date: {datetime.now().strftime('%d %b %Y')}", align="R")
        pdf.ln(8)
        pdf.set_x(15)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(90, 8, f"Phone: {apt.patient.phone}")
        pdf.cell(90, 8, f"Appointment ID: #{apt_id}", align="R")
        pdf.ln(15)
        
        # RX Symbol
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(79, 70, 229) # Indigo
        pdf.cell(0, 10, "Rx", 0, 1)
        pdf.ln(2)
        
        # Diagnosis
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, "Diagnosis & Clinical Notes:", 0, 1)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 6, summary.notes or "No specific diagnosis recorded.")
        pdf.ln(10)
        
        # Medications
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, "Advised Medications:", 0, 1)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 6, summary.medicines or "None prescribed.")
        pdf.ln(15)
        
        # Follow up
        if summary.follow_up_date:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(220, 38, 38) # Red
            pdf.cell(0, 8, f"Follow-up Date: {summary.follow_up_date.strftime('%d %b %Y')}", 0, 1)
            pdf.ln(20)
        else:
            pdf.ln(28)
            
        # Footer / Signature
        pdf.set_draw_color(226, 232, 240)
        pdf.line(130, pdf.get_y(), 190, pdf.get_y())
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 41, 59)
        pdf.set_x(130)
        pdf.cell(60, 8, "Dr. Rudraksh Sharma", 0, 1, "C")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(130)
        pdf.cell(60, 5, "CareDost Clinical Head", 0, 1, "C")
        
        pdf.set_y(-25)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(0, 5, "This is a computer-generated prescription and does not require a physical signature.", 0, 1, "C")
        pdf.cell(0, 5, "CareDost — Your Personalized Clinical Partner", 0, 1, "C")

        # Output to bytes
        pdf_bytes = pdf.output(dest='S')
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=prescription_{apt_id}.pdf'
        return response

    finally:
        db.close()

if __name__ == "__main__":
    app.run(debug=True, port=8000)