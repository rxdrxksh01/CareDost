from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    specialty = Column(String)
    appointments = relationship("Appointment", back_populates="doctor")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String)
    initiation_credits = Column(Integer, default=0)
    reply_credits = Column(Integer, default=0)
    appointments = relationship("Appointment", back_populates="patient")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    appointment_time = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    reminder_sent = Column(Boolean, default=False)
    questionnaire_sent = Column(Boolean, default=False)
    calendar_event_id = Column(String, nullable=True)

    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")

class PatientMessage(Base):
    __tablename__ = "patient_messages"
    
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    message = Column(Text, nullable=True) # Allowed to be null if it's just a file
    file_path = Column(String, nullable=True)
    is_image = Column(Boolean, default=False)
    direction = Column(String, nullable=False) # 'to_patient' or 'from_patient'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="messages")

Patient.messages = relationship("PatientMessage", order_by=PatientMessage.id, back_populates="patient")

class VisitSummary(Base):
    __tablename__ = "visit_summaries"

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    notes = Column(Text)
    medicines = Column(Text)
    follow_up_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    appointment = relationship("Appointment", backref="summary")

class MedicationReminder(Base):
    __tablename__ = "medication_reminders"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    medicine_name = Column(String)
    timing = Column(String)  # morning, afternoon, evening, night
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    active = Column(Boolean, default=True)
    patient = relationship("Patient", backref="reminders")

class PreVisitForm(Base):
    __tablename__ = "pre_visit_forms"

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    main_problem = Column(String)        # fever / cough / stomach / pain / other / don't know
    duration = Column(String)            # today / 2-3 days / a week+ / don't know
    severity = Column(String)            # mild / moderate / severe / don't know
    taking_medicine = Column(String)     # yes / no / don't know
    extra_notes = Column(Text)           # free text or skip
    created_at = Column(DateTime, default=datetime.utcnow)

    appointment = relationship("Appointment", backref="pre_visit_form")