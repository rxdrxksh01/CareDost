from fpdf import FPDF
from datetime import datetime
import io

def generate_prescription_pdf(appointment, summary):
    """Generates a professional prescription PDF and returns it as bytes."""
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
    pdf.cell(90, 8, f"Patient: {appointment.patient.name}")
    pdf.cell(90, 8, f"Date: {datetime.now().strftime('%d %b %Y')}", align="R")
    pdf.ln(8)
    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 8, f"Phone: {appointment.patient.phone}")
    pdf.cell(90, 8, f"Appointment ID: #{appointment.id}", align="R")
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
    return pdf.output(dest='S')
