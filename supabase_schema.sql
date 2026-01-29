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
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_expenses_telegram_id ON expenses(telegram_id);
CREATE INDEX IF NOT EXISTS idx_expenses_created_at ON expenses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_bills_telegram_id ON bills(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- ============================================
-- BANK ACCOUNTS - Track multiple bank accounts
-- ============================================
CREATE TABLE IF NOT EXISTS bank_accounts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    bank_name TEXT NOT NULL,
    current_balance DECIMAL(12,2) DEFAULT 0,
    purpose TEXT CHECK (purpose IN ('savings', 'spending', 'allowance', 'emergency')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bank_accounts_telegram_id ON bank_accounts(telegram_id);

-- ============================================
-- CREDIT CARDS - Track credit card balances
-- ============================================
CREATE TABLE IF NOT EXISTS credit_cards (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    card_name TEXT NOT NULL,
    credit_limit DECIMAL(12,2) NOT NULL,
    current_balance DECIMAL(12,2) DEFAULT 0,
    statement_date INTEGER CHECK (statement_date >= 1 AND statement_date <= 31),
    due_date INTEGER CHECK (due_date >= 1 AND due_date <= 31),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_cards_telegram_id ON credit_cards(telegram_id);

-- ============================================
-- SAVINGS GOALS - Track savings & payoff goals (unified)
-- ============================================
CREATE TABLE IF NOT EXISTS savings_goals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    goal_type TEXT CHECK (goal_type IN ('payoff', 'savings', 'purchase')),
    target_amount DECIMAL(12,2) NOT NULL,
    current_amount DECIMAL(12,2) DEFAULT 0,
    monthly_contribution DECIMAL(12,2) DEFAULT 0,
    priority INTEGER DEFAULT 1,
    target_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_savings_goals_telegram_id ON savings_goals(telegram_id);
CREATE INDEX IF NOT EXISTS idx_savings_goals_active ON savings_goals(telegram_id, is_active);

-- ============================================
-- PAY PERIODS - Track bi-weekly salary cycles
-- ============================================
CREATE TABLE IF NOT EXISTS pay_periods (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    expected_income DECIMAL(12,2),
    actual_income DECIMAL(12,2),
    rollover_amount DECIMAL(12,2) DEFAULT 0,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pay_periods_telegram_id ON pay_periods(telegram_id);
CREATE INDEX IF NOT EXISTS idx_pay_periods_current ON pay_periods(telegram_id, is_current);

-- ============================================
-- TRANSACTIONS - Unified transaction log
-- ============================================
CREATE TABLE IF NOT EXISTS transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    account_type TEXT CHECK (account_type IN ('bank', 'credit_card', 'cash')),
    account_id UUID,
    transaction_type TEXT CHECK (transaction_type IN ('deposit', 'withdraw', 'transfer', 'payment', 'expense')),
    amount DECIMAL(12,2) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_telegram_id ON transactions(telegram_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_type, account_id);

-- Success message
SELECT 'All tables created successfully!' AS status;
