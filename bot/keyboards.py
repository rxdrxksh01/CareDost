from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    keyboard = [
        [InlineKeyboardButton("Book Appointment", callback_data="book")],
        [InlineKeyboardButton("My Appointments", callback_data="my_appointments")],
        [InlineKeyboardButton("Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def time_slots(slots):
    keyboard = []
    for slot in slots:
        keyboard.append([
            InlineKeyboardButton(
                f"{slot['time']}",
                callback_data=f"slot_{slot['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def confirm_booking(slot_id):
    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data=f"confirm_{slot_id}")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ── pre-visit questionnaire keyboards ─────────────────────
def pre_visit_problem_kb(apt_id):
    keyboard = [
        [InlineKeyboardButton("Fever", callback_data=f"pv_prob_{apt_id}_Fever")],
        [InlineKeyboardButton("Cough / Cold", callback_data=f"pv_prob_{apt_id}_Cough / Cold")],
        [InlineKeyboardButton("Stomach Issue", callback_data=f"pv_prob_{apt_id}_Stomach Issue")],
        [InlineKeyboardButton("Pain / Body Ache", callback_data=f"pv_prob_{apt_id}_Pain / Body Ache")],
        [InlineKeyboardButton("Other", callback_data=f"pv_prob_{apt_id}_Other")],
        [InlineKeyboardButton("Don't Know", callback_data=f"pv_prob_{apt_id}_Don't Know")],
        [InlineKeyboardButton("Type my own answer", callback_data=f"pv_type_{apt_id}_problem")],
    ]
    return InlineKeyboardMarkup(keyboard)

def pre_visit_duration_kb(apt_id):
    keyboard = [
        [InlineKeyboardButton("Since today", callback_data=f"pv_dur_{apt_id}_Since today")],
        [InlineKeyboardButton("2-3 days", callback_data=f"pv_dur_{apt_id}_2-3 days")],
        [InlineKeyboardButton("A week or more", callback_data=f"pv_dur_{apt_id}_A week or more")],
        [InlineKeyboardButton("Don't Know", callback_data=f"pv_dur_{apt_id}_Don't Know")],
        [InlineKeyboardButton("Type my own answer", callback_data=f"pv_type_{apt_id}_duration")],
    ]
    return InlineKeyboardMarkup(keyboard)

def pre_visit_severity_kb(apt_id):
    keyboard = [
        [InlineKeyboardButton("Mild", callback_data=f"pv_sev_{apt_id}_Mild")],
        [InlineKeyboardButton("Moderate", callback_data=f"pv_sev_{apt_id}_Moderate")],
        [InlineKeyboardButton("Severe", callback_data=f"pv_sev_{apt_id}_Severe")],
        [InlineKeyboardButton("Don't Know", callback_data=f"pv_sev_{apt_id}_Don't Know")],
        [InlineKeyboardButton("Type my own answer", callback_data=f"pv_type_{apt_id}_severity")],
    ]
    return InlineKeyboardMarkup(keyboard)

def pre_visit_medicine_kb(apt_id):
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f"pv_med_{apt_id}_Yes")],
        [InlineKeyboardButton("No", callback_data=f"pv_med_{apt_id}_No")],
        [InlineKeyboardButton("Don't Know", callback_data=f"pv_med_{apt_id}_Don't Know")],
        [InlineKeyboardButton("Type my own answer", callback_data=f"pv_type_{apt_id}_medicine")],
    ]
    return InlineKeyboardMarkup(keyboard)

def pre_visit_skip_kb(apt_id):
    keyboard = [
        [InlineKeyboardButton("Skip", callback_data=f"pv_skip_{apt_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

def pre_visit_review_kb(apt_id):
    keyboard = [
        [InlineKeyboardButton("Submit", callback_data=f"pv_submit_{apt_id}")],
        [InlineKeyboardButton("Start Over", callback_data=f"pv_redo_{apt_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)