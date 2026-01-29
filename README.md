# 🏦 AvecBanker Bot

A personal budget tracking Telegram bot with multi-user support, expense logging, payment reminders, and weekly summaries.

## Features

- 💬 **Quick expense logging** - Just type "lunch 150 needs"
- 📊 **Budget tracking** - Needs, Wants, Savings categories
- 🔔 **Payment reminders** - Auto-reminders 2 days before bills
- 📈 **Weekly summaries** - Every Sunday at 9 AM
- 👥 **Multi-user** - You and your GF can both use it!
- ⚠️ **Overspending alerts** - Warns when budget is running low

---

## 🚀 Setup Guide

### Step 1: Create Telegram Bot (Done ✅)

You already have your bot at `t.me/avecbanker_bot`

⚠️ **IMPORTANT**: Regenerate your token since you shared it publicly!
1. Message @BotFather
2. Send `/revoke`
3. Select your bot
4. Get new token

---

### Step 2: Set Up Supabase Database

#### 2.1 Go to your Supabase project

Open [supabase.com](https://supabase.com) and go to your project.

#### 2.2 Create the tables

Go to **SQL Editor** (left sidebar) and run this SQL:

```sql
-- ============================================
-- AVECBANKER BOT DATABASE SCHEMA
-- Run this in Supabase SQL Editor
-- ============================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    monthly_income DECIMAL(12,2) DEFAULT 0,
    needs_pct INTEGER DEFAULT 40,
    wants_pct INTEGER DEFAULT 20,
    savings_pct INTEGER DEFAULT 15,
    extra_pct INTEGER DEFAULT 25,
    reminders_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Expenses table
CREATE TABLE IF NOT EXISTS expenses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('needs', 'wants', 'savings')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bills table (recurring payments)
CREATE TABLE IF NOT EXISTS bills (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    due_date INTEGER NOT NULL CHECK (due_date >= 1 AND due_date <= 31),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_expenses_telegram_id ON expenses(telegram_id);
CREATE INDEX IF NOT EXISTS idx_expenses_created_at ON expenses(created_at);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_bills_telegram_id ON bills(telegram_id);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE bills ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access
CREATE POLICY "Service role can do everything on users" ON users
    FOR ALL USING (true);

CREATE POLICY "Service role can do everything on expenses" ON expenses
    FOR ALL USING (true);

CREATE POLICY "Service role can do everything on bills" ON bills
    FOR ALL USING (true);
```

#### 2.3 Get your Supabase credentials

1. Go to **Project Settings** (gear icon)
2. Click **API** in the sidebar
3. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY`

---

### Step 3: Deploy to Render (Free & Easy)

Since Railway has OAuth issues, let's use **Render** instead.

#### 3.1 Push code to GitHub

Using Claude Code in your terminal:

```bash
# Navigate to your project
cd budget-bot

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: AvecBanker budget bot"

# Create repo on GitHub (or use GitHub CLI)
# Then add remote and push
git remote add origin https://github.com/YOUR_USERNAME/avecbanker-bot.git
git branch -M main
git push -u origin main
```

#### 3.2 Deploy on Render

1. Go to [render.com](https://render.com) and sign up (free)
2. Click **New +** → **Background Worker**
3. Connect your GitHub account
4. Select your `avecbanker-bot` repository
5. Configure:
   - **Name**: `avecbanker-bot`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

6. Add **Environment Variables** (click "Advanced"):
   ```
   TELEGRAM_BOT_TOKEN = your_new_bot_token
   SUPABASE_URL = https://your-project.supabase.co
   SUPABASE_KEY = your_anon_key
   ```

7. Click **Create Background Worker**

---

### Step 4: Test Your Bot

1. Open Telegram
2. Go to `t.me/avecbanker_bot`
3. Send `/start`
4. Follow the setup prompts!

---

## 📱 How to Use

### Quick Expense Logging

Just type naturally:
```
lunch 150 needs
grab 80 needs
coffee 120 wants
netflix 550 wants
savings 5000 savings
```

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome & quick start |
| `/setup` | Configure your budget |
| `/status` | View current spending |
| `/log` | Log expense with prompts |
| `/history` | Recent expenses |
| `/summary` | Monthly breakdown |
| `/delete` | Remove last expense |
| `/help` | All commands |

### Categories

- **needs** 🍽️ - Food, transport, utilities, essentials
- **wants** 🎮 - Entertainment, shopping, treats
- **savings** 💰 - Money set aside

---

## 👥 Multi-User Setup (For You & GF)

The bot automatically supports multiple users! Each person:

1. Messages the bot on their own Telegram
2. Runs `/start`
3. Runs `/setup` to configure their own budget
4. Has completely separate tracking

You'll each have your own:
- Income settings
- Budget percentages
- Expense history
- Reminders

---

## 🔔 Automatic Reminders

The bot will remind you:

- **2 days before each bill** at 9 AM
- **Weekly summary** every Sunday at 9 AM

---

## 🛠️ Development (Claude Code)

### Local Testing

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Run locally
python bot.py
```

### Project Structure

```
budget-bot/
├── bot.py              # Main bot logic & handlers
├── database.py         # Supabase database operations
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── Procfile           # For deployment
├── .env.example       # Environment template
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

---

## 🔧 Troubleshooting

### Bot not responding?
- Check Render logs for errors
- Verify environment variables are set
- Make sure bot token is correct

### Database errors?
- Verify Supabase URL and key
- Check if tables were created
- Look at Supabase logs

### Reminders not working?
- Bot must be running 24/7 (Render handles this)
- Check timezone is Asia/Manila
- Verify `reminders_enabled` is true in user settings

---

## 📝 License

MIT - Feel free to modify!

---

Made with 💙 for taking control of your finances!
