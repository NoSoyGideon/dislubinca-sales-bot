# 🤖 SuperDislubincaBot (INCABOT)

> **Intelligent Assistant for Sales Management, Collections, and Real-Time Cloud Data Injection**

`SuperDislubincaBot` is a comprehensive Python solution designed for operational automation in distributed sales team routes. It parses daily natural language reports using Gemini AI, tracks collection and unit quotas, consolidates transactions into a local SQLite database, and automatically syncs executive Excel reports in Dropbox.

---

## 🚀 Key Features

- 🧠 **Natural Language Processing (Gemini AI):** Interprets unformatted natural language text sent by sales reps (morning sales plans and evening closing reports broken down by foreign currencies, Zelle, cash, and local currency).
- 📊 **Dynamic Excel Injection & Closing:** Automatically generates and injects daily data into monthly and weekly templates hosted on Dropbox using `openpyxl`.
- 🗄️ **Robust Data Architecture:** Data persistence managed via SQLite with the Repository Pattern for fast and thread-safe transactions.
- 🛠️ **CLI Management Panel:** Includes `incacli.py`, an interactive terminal tool for user authorization, route management, role elevation, database log auditing, and test data cleanup.
- 👥 **Role & Permission Management:** Differentiated command menu and workflows for **Supervisors/Admins** and **Sales Representatives** assigned to specific routes.
- ⚡ **Resilience & Error Handling:** Built-in safeguards against network drops, Dropbox API rate limits, and strict schema validation for LLM JSON outputs.

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Bot Framework:** `python-telegram-bot` (v20+)
- **AI / NLP:** Google Gemini API (`google-genai`)
- **Data & Cloud Processing:** `pandas`, `openpyxl`, `dropbox`
- **Database:** SQLite3
- **Environment Management:** `python-dotenv`

---

## 📁 Repository Structure

```text
SuperDislubincaBot/
├── config/             # Environment configuration & global settings
├── src/
│   ├── bot/            # Telegram handlers, keyboards, and flow management
│   ├── database/       # SQLite Repositories & DB Schema initialization
│   │   ├── connection.py
│   │   ├── init_db.py  # Script to initialize tables and schema
│   │   └── ...
│   └── services/       # Integrations for Gemini AI, Dropbox, and Excel Services
│   ├── incacli.py          # Interactive Admin CLI tool for user and DB management
│   ├── main.py             # Main application entry point for Telegram bot
├── templates/          # Master Excel workbook templates
└── requirements.txt    # Project dependencies
```

---

## ⚙️ Setup and Installation

### 1. Clone the repository

```bash
git clone [https://github.com/NoSoyGideon/SuperDislubincaBot.git](https://github.com/NoSoyGideon/SuperDislubincaBot.git)
cd SuperDislubincaBot
```

### 2. Create and activate virtual environment

```bash
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your API keys and credentials:

```bash
cp .env.example .env
```

Example `.env`:

```ini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
DROPBOX_REFRESH_TOKEN=your_dropbox_refresh_token
DROPBOX_APP_KEY=your_dropbox_app_key
DROPBOX_APP_SECRET=your_dropbox_app_secret
DB_PATH=database/disulubinca.db
```

### 5. Initialize the Database Schema

Before starting the bot for the first time, execute the initialization script to create the necessary SQLite database tables (`usuarios`, `registros_diarios`, `logs`, etc.):

```bash
python src/database/init_db.py
```

### 6. Run the Application

```bash
python main.py
```

---

## ⚙️ Administration & CLI Tool (`incacli.py`)

The repository includes a Command-Line Interface (`incacli.py`) for system administration without needing direct SQLite manipulation.

To launch the management panel:

```bash
python incacli.py
```

**Available CLI Options:**
1. 👥 View all registered users and their status.
2. 🔑 Authorize / Create a Sales Representative (Assign Route).
3. 🚫 Ban / Block users.
4. 🪵 Audit system logs.
5. 🗑️ Clear all database logs.
6. 💥 Clean test data (resets sales & collection logs).
7. 👑 Change User Role (`Sales Rep` ↔ `Supervisor`).

---

## ✒️ Author

- **Orlando Marcano** - [GitHub Profile](https://github.com/NoSoyGideon)
