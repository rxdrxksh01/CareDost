# CareDost

A Telegram-based clinic management system that automates appointment booking, patient communication, and post-visit care — designed for small clinics that still rely on manual workflows.

---

##  Overview

CareDost eliminates the need for phone calls, paper registers, and manual follow-ups.

Patients can:

* Book appointments directly via Telegram
* Receive automated reminders
* Access prescriptions digitally
* Get medication notifications

Doctors get:

* A centralized dashboard
* Real-time appointment tracking
* Structured patient records

---

##  Key Features

### Patient Experience (Telegram Bot)

* Simple onboarding (name + phone)
* Real-time slot booking
* Automated appointment reminders
* Digital prescriptions & visit summaries
* Scheduled medication alerts
* Appointment history tracking

### Doctor Dashboard (Web App)

* Secure login system
* Daily + upcoming appointment view
* Patient & visit management
* Prescription and follow-up tracking
* Instant patient notifications

---

##  System Design Highlights

* Event-driven architecture for reminders and notifications
* Calendar synchronization to avoid double-booking
* Fail-safe booking system (graceful fallback when external APIs fail)
* Stateful conversations for seamless user experience
* Timezone-safe scheduling (IST ↔ UTC handling)

---

##  Tech Stack

| Layer       | Technology                   |
| ----------- | ---------------------------- |
| Bot         | Python (python-telegram-bot) |
| Backend     | Flask                        |
| Database    | SQLite + SQLAlchemy          |
| Scheduling  | APScheduler                  |
| Integration | Google Calendar API          |

---

##  Project Structure

```
clinic-bot/
├── bot/            # Telegram bot logic
├── dashboard/      # Doctor web interface
├── scheduler/      # Background jobs (reminders)
├── db/             # Database models & setup
├── main.py         # Entry point
```

---

##  Setup (Quick Start)

```bash
git clone https://github.com/YOUR_USERNAME/caredost.git
cd caredost
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```env
TELEGRAM_BOT_TOKEN=your_token
DATABASE_URL=sqlite:///clinic.db
SECRET_KEY=your_secret
```

Run:

```bash
python main.py
python -m dashboard.app
```

---


##  Production Improvements (Planned)

* PostgreSQL instead of SQLite
* Webhooks instead of polling
* Celery + Redis for scalable background jobs
* Multi-doctor support with OAuth
* Cloud deployment (Railway / Render)

---

Built by Rudraksh Sharma
