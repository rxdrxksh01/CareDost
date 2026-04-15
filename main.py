from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)
from bot.handlers import (
    start, ask_name, ask_phone, menu_callback,
    slot_selected, confirm_slot, cancel,
    ASK_NAME, ASK_PHONE
)
from scheduler.reminders import start_scheduler, scheduler
from db.database import init_db, SessionLocal
from db.models import Doctor
import os
from dotenv import load_dotenv

load_dotenv()

def seed_doctor():
    db = SessionLocal()
    if not db.query(Doctor).first():
        doctor = Doctor(name="Dr. Rudraksh Sharma", specialty="General Physician")
        db.add(doctor)
        db.commit()
        print("Doctor seeded.")
    db.close()

def get_bot():
    from telegram import Bot
    import os
    return Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))

async def post_init(application):
    start_scheduler(application.bot)
    from scheduler.reminders import start_medication_scheduler
    start_medication_scheduler(application.bot)
    scheduler.start()
    print("⏰ Reminder scheduler started.")

def main():
    init_db()
    seed_doctor()

    app = (
        ApplicationBuilder()
        .token(os.getenv("TELEGRAM_BOT_TOKEN"))
        .post_init(post_init)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(slot_selected, pattern="^slot_"))
    app.add_handler(CallbackQueryHandler(confirm_slot, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(menu_callback))

    print("🚀 CareDost bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()