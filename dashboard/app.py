from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from db.database import SessionLocal
from db.models import Doctor, Patient, Appointment, VisitSummary, MedicationReminder
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
        if username == "doctor" and password == "caredost123":
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
        if summary:
            summary_data = {
                "notes": summary.notes,
                "medicines": summary.medicines,
                "follow_up_date": summary.follow_up_date
            }

    finally:
        db.close()

    if request.method == "POST":
        notes = request.form.get("notes", "")
        medicines = request.form.get("medicines", "")
        follow_up = request.form.get("follow_up", "")

        db = SessionLocal()
        try:
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
        except Exception as e:
            print(f"Notification error: {e}")

        return redirect(url_for("dashboard"))

    return render_template("appointment.html",
        apt={"id": apt_id, "time": apt_time, "status": apt_status},
        patient={"name": patient_name, "phone": patient_phone},
        summary=summary_data
    )



if __name__ == "__main__":
    app.run(debug=True, port=5000)