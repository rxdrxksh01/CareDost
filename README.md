# CareDost

A Telegram-based clinic management system that automates appointment booking, patient communication, and post-visit care — designed for small clinics looking to modernize their workflows.

---

## 🏥 Overview

CareDost eliminates the need for phone calls, paper registers, and manual follow-ups.

**Patients can:**
* Book appointments directly via Telegram
* Receive automated reminders (2 hours before)
* Complete pre-visit questionnaires digitially
* Access prescriptions and visit summaries

**Doctors get:**
* A centralized web dashboard
* AI-powered note expansion for quick consulting
* Real-time appointment tracking and patient chat history
* Automated medication reminders for patients

---

## ✨ Key Features

### Patient Experience (Telegram Bot)
* **Simple Onboarding:** Fast registration via name and phone.
* **Real-time Slot Booking:** Integrated with Google Calendar to prevent double-booking.
* **Automated Schedulers:** Reminders and pre-visit forms sent automatically via background jobs.
* **Visit Logic:** Receive digital visit summaries and medication alerts directly in chat.

### Doctor Dashboard (Web App)
* **Secure Access:** Environment-based credential management.
* **Patient Overview:** Searchable history including past messages and uploaded medical files.
* **Smart Consulting:** Use medical shorthand and expand it into professional notes using AI (Llama 3).
* **Mass Communication:** Broadcast updates or emergency cancellations to all patients of a specific day.

---

## 🛠 Tech Stack

| Layer       | Technology                   |
| ----------- | ---------------------------- |
| **Bot**     | Python (python-telegram-bot) |
| **Backend** | Flask (Web Dashboard)        |
| **Database**| SQLite (Development) / PostgreSQL (Production) |
| **AI**      | Groq Cloud (Llama 3.3 70B)   |
| **Calendar**| Google Calendar API          |

---

## 🚀 Setup Guide

### 1. Installation
```bash
git clone https://github.com/rxdrxksh01/CareDost.git
cd CareDost
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_URL=sqlite:///clinic.db
GROQ_API_KEY=your_groq_key
DASHBOARD_USERNAME=doctor
DASHBOARD_PASSWORD=your_secure_password
SECRET_KEY=your_flask_secret
```

### 3. Google Calendar Integration
1. Place your `credentials.json` in the root folder.
2. The first time you run the bot, it will prompt you to authenticate via browser to generate `token.pickle`.

### 4. Running the App
Start the bot and the dashboard:
```bash
# Terminal 1: Start the Telegram Bot & Schedulers
python main.py

# Terminal 2: Start the Doctor Dashboard
python -m dashboard.app
```

---

## 🏗 Planned Production Improvements
* **Database:** Migration to PostgreSQL for production environments.
* **Scalability:** Celery + Redis for high-concurrency background notifications.
* **Webhooks:** Transition from polling to webhooks for production bot deployment.
* **Multi-tenancy:** OAuth integration for multi-doctor support.

---
Built with ❤️ by Rudraksh Sharma
