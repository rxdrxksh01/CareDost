from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from db.database import SessionLocal
from db.models import Doctor, Patient, Appointment, VisitSummary
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
    apt = db.query(Appointment).filter(Appointment.id == apt_id).first()

    if not apt:
        db.close()
        return redirect(url_for("dashboard"))

    patient = db.query(Patient).filter(Patient.id == apt.patient_id).first()
    summary = db.query(VisitSummary).filter(
        VisitSummary.appointment_id == apt_id
    ).first()

    if request.method == "POST":
        notes = request.form.get("notes", "")
        medicines = request.form.get("medicines", "")
        follow_up = request.form.get("follow_up", "")

        if summary:
            summary.notes = notes
            summary.medicines = medicines
            if follow_up:
                summary.follow_up_date = datetime.strptime(follow_up, "%Y-%m-%d")
        else:
            summary = VisitSummary(
                appointment_id=apt_id,
                notes=notes,
                medicines=medicines,
                follow_up_date=datetime.strptime(follow_up, "%Y-%m-%d") if follow_up else None
            )
            db.add(summary)

        apt.status = "completed"
        db.commit()
        db.close()
        return redirect(url_for("dashboard"))

    db.close()
    return render_template("appointment.html",
        apt=apt,
        patient=patient,
        summary=summary
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)