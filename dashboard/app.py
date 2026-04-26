from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import io
import os
from db.database import SessionLocal
from db.models import Doctor, Patient, Appointment, VisitSummary, MedicationReminder, PreVisitForm, PatientMessage
from utils.pdf_generator import generate_prescription_pdf
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "caredost-secret-2026")

# Register REST API for React dashboard
from dashboard.api import api as api_blueprint
app.register_blueprint(api_blueprint)

# CORS for React dev server
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "")
    if "localhost" in origin or "127.0.0.1" in origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

# ── React SPA Serving ─────────────────────────────────────
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dashboard-ui', 'dist'))
    index_path = os.path.join(dist_dir, 'index.html')

    # Helpful fallback instead of 500 when frontend build is missing.
    if not os.path.exists(index_path):
        return (
            "Frontend build missing. Run: npm --prefix dashboard-ui install && npm --prefix dashboard-ui run build",
            503,
        )

    # If the file exists in the dist folder, serve it (like assets/xxx.js)
    if path != "" and os.path.exists(os.path.join(dist_dir, path)):
        from flask import send_from_directory
        return send_from_directory(dist_dir, path)
    
    # Otherwise, return index.html for React Router
    from flask import send_from_directory
    return send_from_directory(dist_dir, 'index.html')


@app.route("/health")
def health():
    return jsonify({"ok": True}), 200

# ── prescription download ─────────────────────────────────
@app.route("/appointment/<int:apt_id>/prescription")
def download_prescription_route(apt_id):
    db = SessionLocal()
    try:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt: return "Appointment not found", 404
        summary = db.query(VisitSummary).filter(VisitSummary.appointment_id == apt_id).first()
        if not summary: return "No visit notes found.", 400
        
        from utils.pdf_generator import generate_prescription_pdf
        pdf_bytes = generate_prescription_pdf(apt, summary)
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=prescription_{apt_id}.pdf'
        return response
    finally:
        db.close()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "8000")))
