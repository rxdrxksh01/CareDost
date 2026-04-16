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
    from scheduler.reminders import start_medication_scheduler, start_pre_visit_scheduler
    start_medication_scheduler(application.bot)
    start_pre_visit_scheduler(application.bot)
    scheduler.start()
    print("⏰ All schedulers started.")

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

    # pre-visit questionnaire handlers
    from bot.pre_visit import (
        pv_problem_callback, pv_duration_callback,
        pv_severity_callback, pv_medicine_callback,
        pv_skip_callback, pv_free_text_handler,
        pv_type_callback, pv_submit_callback, pv_redo_callback
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(slot_selected, pattern="^slot_"))
    app.add_handler(CallbackQueryHandler(confirm_slot, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(pv_problem_callback, pattern="^pv_prob_"))
    app.add_handler(CallbackQueryHandler(pv_duration_callback, pattern="^pv_dur_"))
    app.add_handler(CallbackQueryHandler(pv_severity_callback, pattern="^pv_sev_"))
    app.add_handler(CallbackQueryHandler(pv_medicine_callback, pattern="^pv_med_"))
    app.add_handler(CallbackQueryHandler(pv_skip_callback, pattern="^pv_skip_"))
    app.add_handler(CallbackQueryHandler(pv_type_callback, pattern="^pv_type_"))
    app.add_handler(CallbackQueryHandler(pv_submit_callback, pattern="^pv_submit_"))
    app.add_handler(CallbackQueryHandler(pv_redo_callback, pattern="^pv_redo_"))
    app.add_handler(CallbackQueryHandler(menu_callback))
    # free-text handler for pre-visit notes (must be after conv_handler)
    from bot.handlers import patient_reply_handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pv_free_text_handler))
    # Put patient replies in a separate group so they are caught even if other handlers run
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, patient_reply_handler), group=2)

    print("🚀 CareDost bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()