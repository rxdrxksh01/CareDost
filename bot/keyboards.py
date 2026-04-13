from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📅 Book Appointment", callback_data="book")],
        [InlineKeyboardButton("📋 My Appointments", callback_data="my_appointments")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def time_slots(slots):
    keyboard = []
    for slot in slots:
        keyboard.append([
            InlineKeyboardButton(
                f"🕐 {slot['time']}",
                callback_data=f"slot_{slot['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def confirm_booking(slot_id):
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{slot_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)