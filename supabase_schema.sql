-- ============================================
-- AVECBANKER BOT DATABASE SCHEMA
-- Copy and paste this ENTIRE script into Supabase SQL Editor
-- ============================================

-- Users table - stores each person's settings
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

-- Expenses table - stores all logged expenses
CREATE TABLE IF NOT EXISTS expenses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('needs', 'wants', 'savings')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bills table - stores recurring monthly bills
CREATE TABLE IF NOT EXISTS bills (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    due_date INTEGER NOT NULL CHECK (due_date >= 1 AND due_date <= 31),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_expenses_telegram_id ON expenses(telegram_id);
CREATE INDEX IF NOT EXISTS idx_expenses_created_at ON expenses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_bills_telegram_id ON bills(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- Success message
SELECT 'All tables created successfully!' AS status;
