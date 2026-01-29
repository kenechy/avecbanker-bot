"""
AvecBanker Bot - PythonAnywhere Version
Uses Flask webhook with synchronous HTTP requests
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from database import Database
from calculator import GoalCalculator

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize
db = Database()

# Flask app for webhook
flask_app = Flask(__name__)

# Bot token
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Simple user state storage (for setup wizard)
user_states = {}


# ============ TELEGRAM API HELPERS ============

def send_message(chat_id, text, parse_mode="Markdown", reply_markup=None):
    """Send a message via Telegram API"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None


def edit_message(chat_id, message_id, text, parse_mode="Markdown"):
    """Edit a message via Telegram API"""
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }

    try:
        response = requests.post(f"{API_URL}/editMessageText", json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Edit message error: {e}")
        return None


def answer_callback(callback_id):
    """Answer callback query"""
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": callback_id}, timeout=5)
    except Exception as e:
        logger.error(f"Answer callback error: {e}")


# ============ HELPER FUNCTIONS ============

def format_currency(amount: float) -> str:
    """Format number as Philippine Peso"""
    return f"₱{amount:,.2f}"


def get_progress_bar(percentage: float, length: int = 10) -> str:
    """Create a visual progress bar"""
    filled = int(min(percentage, 100) / 100 * length)
    empty = length - filled
    if percentage >= 90:
        return "🔴" * filled + "⬜" * empty
    elif percentage >= 70:
        return "🟡" * filled + "⬜" * empty
    else:
        return "🟢" * filled + "⬜" * empty


def get_or_create_user(telegram_id: int, username: str = None) -> dict:
    """Get existing user or create new one"""
    user = db.get_user_sync(telegram_id)
    if not user:
        user = db.create_user_sync(telegram_id, username)
    return user


# ============ COMMAND HANDLERS ============

def handle_start(chat_id, user_id, first_name, username):
    """Welcome message"""
    get_or_create_user(user_id, username)

    welcome_msg = f"""🏦 *Welcome to AvecBanker Bot!*

Hello {first_name}! I'm your personal budget assistant.

*Quick Start:*
1️⃣ Set up your budget: /setup
2️⃣ Log expense: Just type like "lunch 150 needs"
3️⃣ Check status: /status

*Commands:*
/setup - Configure your monthly budget
/status - View current spending
/history - View recent expenses
/summary - Weekly/monthly summary
/help - Full command list

Let's take control of your finances! 💪"""

    send_message(chat_id, welcome_msg)


def handle_setup(chat_id, user_id, username):
    """Interactive budget setup"""
    get_or_create_user(user_id, username)

    reply_markup = {
        "inline_keyboard": [
            [{"text": "💰 Set Income", "callback_data": "setup_income"}],
            [{"text": "📋 Set Fixed Bills", "callback_data": "setup_bills"}],
            [{"text": "📊 Set Budget Split", "callback_data": "setup_budget"}],
            [{"text": "✅ View Current Setup", "callback_data": "setup_view"}],
        ]
    }

    send_message(
        chat_id,
        "⚙️ *Budget Setup*\n\nWhat would you like to configure?",
        reply_markup=reply_markup
    )


def handle_status(chat_id, user_id, username):
    """Show current budget status"""
    user = get_or_create_user(user_id, username)

    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    expenses = db.get_expenses_sync(user_id, month_start)
    bills = db.get_bills_sync(user_id)

    income = user.get("monthly_income", 0) if user else 0
    total_bills = sum(b["amount"] for b in bills)
    available = income - total_bills

    needs_budget = available * (user.get("needs_pct", 40) if user else 40) / 100
    wants_budget = available * (user.get("wants_pct", 20) if user else 20) / 100
    savings_budget = available * (user.get("savings_pct", 15) if user else 15) / 100

    needs_spent = sum(e["amount"] for e in expenses if e["category"] == "needs")
    wants_spent = sum(e["amount"] for e in expenses if e["category"] == "wants")

    needs_pct = (needs_spent / needs_budget * 100) if needs_budget > 0 else 0
    wants_pct = (wants_spent / wants_budget * 100) if wants_budget > 0 else 0

    days_in_month = 30
    days_remaining = max(days_in_month - now.day, 1)

    needs_daily = (needs_budget - needs_spent) / days_remaining
    wants_daily = (wants_budget - wants_spent) / days_remaining

    status_msg = f"""📊 *Budget Status - {now.strftime('%B %Y')}*

💰 *Income:* {format_currency(income)}
📋 *Fixed Bills:* {format_currency(total_bills)}
💵 *Available:* {format_currency(available)}

━━━━━━━━━━━━━━━━━━━━

🍽️ *NEEDS*
{get_progress_bar(needs_pct)} {needs_pct:.0f}%
Spent: {format_currency(needs_spent)} / {format_currency(needs_budget)}
📅 Daily limit: {format_currency(needs_daily)}

🎮 *WANTS*
{get_progress_bar(wants_pct)} {wants_pct:.0f}%
Spent: {format_currency(wants_spent)} / {format_currency(wants_budget)}
📅 Daily limit: {format_currency(wants_daily)}

💰 *SAVINGS TARGET:* {format_currency(savings_budget)}

━━━━━━━━━━━━━━━━━━━━
📅 {days_remaining} days remaining this month"""

    if needs_pct >= 90:
        status_msg += "\n🚨 *WARNING: Needs budget almost depleted!*"
    if wants_pct >= 90:
        status_msg += "\n🚨 *WARNING: Wants budget almost depleted!*"

    send_message(chat_id, status_msg)


def handle_history(chat_id, user_id):
    """Show recent expenses"""
    expenses = db.get_recent_expenses_sync(user_id, limit=10)

    if not expenses:
        send_message(chat_id, "No expenses recorded yet!")
        return

    history_msg = "📜 *Recent Expenses*\n\n"

    for e in expenses:
        date = e["created_at"].strftime("%m/%d") if isinstance(e["created_at"], datetime) else str(e["created_at"])[:5]
        category_emoji = {"needs": "🍽️", "wants": "🎮", "savings": "💰"}
        emoji = category_emoji.get(e["category"], "📝")
        history_msg += f"{date} {emoji} {e['description'].title()}: {format_currency(e['amount'])}\n"

    send_message(chat_id, history_msg)


def handle_summary(chat_id, user_id):
    """Monthly summary"""
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    expenses = db.get_expenses_sync(user_id, month_start)

    by_category = {"needs": [], "wants": [], "savings": []}
    for e in expenses:
        if e["category"] in by_category:
            by_category[e["category"]].append(e)

    summary_msg = f"📈 *Monthly Summary - {now.strftime('%B %Y')}*\n\n"

    for category, items in by_category.items():
        total = sum(e["amount"] for e in items)
        count = len(items)
        emoji = {"needs": "🍽️", "wants": "🎮", "savings": "💰"}[category]

        summary_msg += f"{emoji} *{category.upper()}*: {format_currency(total)} ({count} items)\n"

    total_spent = sum(e["amount"] for e in expenses if e["category"] != "savings")

    summary_msg += f"\n💸 *Total Spent:* {format_currency(total_spent)}"

    send_message(chat_id, summary_msg)


def handle_help(chat_id):
    """Show all commands"""
    help_text = """📖 *AvecBanker Bot Commands*

*Setup:*
/start - Welcome & quick start
/setup - Configure your budget

*Daily Use:*
• Just type: `lunch 150 needs`
• Credit card: `cc 500 shoes`
• Deposit: `deposit 5000 bpi`
• Withdraw: `withdraw 1000 unionbank`
/status - Current budget status

*Banking:*
/banks - View all bank accounts
/addbank - Add a bank account
/transfer - Transfer between accounts

*Credit Cards:*
/cc - View credit card status
/addcc - Add a credit card
/ccpay - Log credit card payment

*Goals & Payoff:*
/goals - View all goals
/addgoal - Add savings/payoff goal
/payoff - View payoff progress

*Pay Periods:*
/payday - Log payday, start new period

*Reports:*
/dashboard - Full financial overview
/bills - Upcoming bills
/history - Recent expenses
/summary - Monthly breakdown

*Categories:*
• `needs` - Food, transport, essentials
• `wants` - Entertainment, shopping
• `savings` - Money saved"""

    send_message(chat_id, help_text)


# ============ BANK ACCOUNT HANDLERS ============

def handle_banks(chat_id, user_id):
    """Show all bank accounts"""
    accounts = db.get_bank_accounts_sync(user_id)

    if not accounts:
        send_message(chat_id, "🏦 No bank accounts set up yet.\n\nUse /addbank to add your first account!")
        return

    total = sum(a.get("current_balance", 0) for a in accounts)

    msg = "🏦 *Your Bank Accounts*\n\n"
    for a in accounts:
        balance = a.get("current_balance", 0)
        purpose = a.get("purpose", "")
        purpose_emoji = {"savings": "💰", "spending": "💳", "allowance": "🎮", "emergency": "🚨"}.get(purpose, "🏦")
        purpose_text = f" ({purpose})" if purpose else ""
        msg += f"{purpose_emoji} *{a['bank_name']}*: {format_currency(balance)}{purpose_text}\n"

    msg += f"\n━━━━━━━━━━━━━━━━━━━━\n💵 *Total:* {format_currency(total)}"

    send_message(chat_id, msg)


def handle_addbank(chat_id, user_id):
    """Start adding a bank account"""
    user_states[user_id] = "addbank"
    send_message(
        chat_id,
        "🏦 *Add Bank Account*\n\n"
        "Enter in format:\n"
        "`bank_name balance purpose`\n\n"
        "Purpose: savings, spending, allowance, emergency\n\n"
        "Example:\n"
        "`UnionBank 3300 savings`\n"
        "`BPI 10600 spending`\n"
        "`Maya 0 allowance`"
    )


def handle_deposit(chat_id, user_id, bank_name: str = None, amount: float = None):
    """Handle deposit to bank account"""
    if bank_name and amount:
        account = db.get_bank_account_by_name_sync(user_id, bank_name)
        if account:
            new_balance = account["current_balance"] + amount
            db.update_bank_balance_sync(account["id"], new_balance)
            db.add_transaction_sync(user_id, "bank", account["id"], "deposit", amount, f"Deposit to {bank_name}")
            send_message(
                chat_id,
                f"✅ Deposited {format_currency(amount)} to *{account['bank_name']}*\n"
                f"New balance: {format_currency(new_balance)}"
            )
        else:
            send_message(chat_id, f"❌ Bank account '{bank_name}' not found. Use /banks to see your accounts.")
    else:
        user_states[user_id] = "deposit"
        send_message(
            chat_id,
            "💵 *Deposit Money*\n\n"
            "Enter: `amount bank_name`\n"
            "Example: `5000 BPI`"
        )


def handle_withdraw(chat_id, user_id, bank_name: str = None, amount: float = None):
    """Handle withdrawal from bank account"""
    if bank_name and amount:
        account = db.get_bank_account_by_name_sync(user_id, bank_name)
        if account:
            if account["current_balance"] >= amount:
                new_balance = account["current_balance"] - amount
                db.update_bank_balance_sync(account["id"], new_balance)
                db.add_transaction_sync(user_id, "bank", account["id"], "withdraw", amount, f"Withdraw from {bank_name}")
                send_message(
                    chat_id,
                    f"✅ Withdrew {format_currency(amount)} from *{account['bank_name']}*\n"
                    f"New balance: {format_currency(new_balance)}"
                )
            else:
                send_message(chat_id, f"❌ Insufficient balance. Current: {format_currency(account['current_balance'])}")
        else:
            send_message(chat_id, f"❌ Bank account '{bank_name}' not found.")
    else:
        user_states[user_id] = "withdraw"
        send_message(
            chat_id,
            "💸 *Withdraw Money*\n\n"
            "Enter: `amount bank_name`\n"
            "Example: `1000 UnionBank`"
        )


def handle_transfer(chat_id, user_id):
    """Start transfer between accounts"""
    user_states[user_id] = "transfer"
    accounts = db.get_bank_accounts_sync(user_id)
    if not accounts:
        send_message(chat_id, "❌ No bank accounts set up. Use /addbank first.")
        return

    accounts_list = ", ".join([a["bank_name"] for a in accounts])
    send_message(
        chat_id,
        "🔄 *Transfer Between Accounts*\n\n"
        f"Your accounts: {accounts_list}\n\n"
        "Enter: `from_bank to_bank amount`\n"
        "Example: `BPI UnionBank 5000`"
    )


# ============ CREDIT CARD HANDLERS ============

def handle_cc(chat_id, user_id):
    """Show credit card status"""
    cards = db.get_credit_cards_sync(user_id)

    if not cards:
        send_message(chat_id, "💳 No credit cards set up yet.\n\nUse /addcc to add one!")
        return

    msg = "💳 *Your Credit Cards*\n\n"
    for c in cards:
        balance = c.get("current_balance", 0)
        limit = c.get("credit_limit", 0)
        utilization = (balance / limit * 100) if limit > 0 else 0
        due_date = c.get("due_date")
        due_text = f" (due: {due_date}th)" if due_date else ""

        msg += f"*{c['card_name']}*{due_text}\n"
        msg += f"{get_progress_bar(utilization)} {utilization:.0f}%\n"
        msg += f"{format_currency(balance)} / {format_currency(limit)}\n\n"

    total_balance = sum(c.get("current_balance", 0) for c in cards)
    total_limit = sum(c.get("credit_limit", 0) for c in cards)
    msg += f"━━━━━━━━━━━━━━━━━━━━\n💳 *Total:* {format_currency(total_balance)} / {format_currency(total_limit)}"

    send_message(chat_id, msg)


def handle_addcc(chat_id, user_id):
    """Start adding a credit card"""
    user_states[user_id] = "addcc"
    send_message(
        chat_id,
        "💳 *Add Credit Card*\n\n"
        "Enter in format:\n"
        "`card_name limit due_date`\n\n"
        "Example:\n"
        "`BDO 50000 15`\n"
        "`Metrobank 100000 25`"
    )


def handle_ccpay(chat_id, user_id):
    """Log credit card payment"""
    user_states[user_id] = "ccpay"
    cards = db.get_credit_cards_sync(user_id)
    if not cards:
        send_message(chat_id, "❌ No credit cards set up. Use /addcc first.")
        return

    cards_list = ", ".join([f"{c['card_name']} ({format_currency(c.get('current_balance', 0))})" for c in cards])
    send_message(
        chat_id,
        "💳 *Pay Credit Card*\n\n"
        f"Your cards: {cards_list}\n\n"
        "Enter: `card_name amount`\n"
        "Example: `BDO 5000`"
    )


def handle_ccspend(chat_id, user_id, card_name: str, amount: float, description: str = ""):
    """Log credit card spend"""
    # Try to find card, default to first card if only one exists
    cards = db.get_credit_cards_sync(user_id)

    if not cards:
        send_message(chat_id, "❌ No credit cards set up. Use /addcc first.")
        return

    card = None
    if card_name:
        card = db.get_credit_card_by_name_sync(user_id, card_name)

    if not card and len(cards) == 1:
        card = cards[0]

    if card:
        new_balance = card["current_balance"] + amount
        db.update_credit_card_balance_sync(card["id"], new_balance)
        db.add_transaction_sync(user_id, "credit_card", card["id"], "expense", amount, description)

        limit = card.get("credit_limit", 0)
        utilization = (new_balance / limit * 100) if limit > 0 else 0

        send_message(
            chat_id,
            f"💳 *{card['card_name']}* +{format_currency(amount)}\n"
            f"{description.title() if description else 'Expense'}\n"
            f"{get_progress_bar(utilization)} {utilization:.0f}%\n"
            f"Balance: {format_currency(new_balance)}"
        )
    else:
        send_message(chat_id, f"❌ Card '{card_name}' not found. Use /cc to see your cards.")


# ============ GOALS & PAYOFF HANDLERS ============

def handle_goals(chat_id, user_id):
    """Show all active goals"""
    goals = db.get_goals_sync(user_id)

    if not goals:
        send_message(chat_id, "🎯 No goals set up yet.\n\nUse /addgoal to add one!")
        return

    msg = "🎯 *Your Goals*\n\n"

    for g in goals:
        current = g.get("current_amount", 0)
        target = g.get("target_amount", 0)
        progress = (current / target * 100) if target > 0 else 0
        monthly = g.get("monthly_contribution", 0)
        goal_type = g.get("goal_type", "savings")
        priority = g.get("priority", 1)

        type_emoji = {"payoff": "🏍️", "savings": "💰", "purchase": "🛒"}.get(goal_type, "🎯")

        msg += f"{type_emoji} *{g['name']}* (P{priority})\n"
        msg += f"{get_progress_bar(progress, 10)} {progress:.0f}%\n"
        msg += f"{format_currency(current)} / {format_currency(target)}\n"
        if monthly > 0:
            msg += f"📅 Monthly: {format_currency(monthly)}\n"
        if g.get("target_date"):
            msg += f"🎯 Target: {g['target_date']}\n"
        msg += "\n"

    send_message(chat_id, msg)


def handle_payoff(chat_id, user_id):
    """Show payoff goals progress (filtered view)"""
    goals = db.get_goals_sync(user_id)
    payoff_goals = [g for g in goals if g.get("goal_type") == "payoff"]

    if not payoff_goals:
        send_message(chat_id, "🏍️ No payoff goals set up.\n\nUse /addgoal to add one!")
        return

    msg = "🏍️ *Payoff Goals Progress*\n\n"

    for g in payoff_goals:
        current = g.get("current_amount", 0)
        target = g.get("target_amount", 0)
        remaining = target - current
        progress = (current / target * 100) if target > 0 else 0
        monthly = g.get("monthly_contribution", 0)

        msg += f"*{g['name']}*\n"
        msg += f"{'█' * int(progress / 10)}{'░' * (10 - int(progress / 10))} {progress:.0f}%\n"
        msg += f"{format_currency(current)} / {format_currency(target)}\n"
        msg += f"Remaining: {format_currency(remaining)}\n"

        if monthly > 0:
            months_left = remaining / monthly if monthly > 0 else 0
            msg += f"📅 At {format_currency(monthly)}/month: {months_left:.1f} months\n"

        if g.get("target_date"):
            msg += f"🎯 Target: {g['target_date']}\n"

        msg += "\n"

    send_message(chat_id, msg)


def handle_addgoal(chat_id, user_id):
    """Start adding a goal"""
    user_states[user_id] = "addgoal"
    send_message(
        chat_id,
        "🎯 *Add a Goal*\n\n"
        "Enter in format:\n"
        "`name type target_amount monthly_payment target_date`\n\n"
        "Types: payoff, savings, purchase\n\n"
        "Examples:\n"
        "`motorcycle payoff 208000 6500 2024-09-01`\n"
        "`iphone purchase 70000 7200 2024-12-01`\n"
        "`emergency savings 100000 5000`"
    )


def handle_paid_goal(chat_id, user_id, goal_name: str, amount: float = None):
    """Handle payment to a goal"""
    goal = db.get_goal_by_name_sync(user_id, goal_name)

    if not goal:
        send_message(chat_id, f"❌ Goal '{goal_name}' not found. Use /goals to see your goals.")
        return

    if amount is None:
        amount = goal.get("monthly_contribution", 0)

    if amount <= 0:
        send_message(chat_id, "❌ Please specify an amount.")
        return

    db.add_goal_payment_sync(goal["id"], amount)
    db.add_transaction_sync(user_id, "cash", None, "payment", amount, f"Payment to {goal_name}")

    updated_goal = db.get_goal_by_name_sync(user_id, goal_name)
    current = updated_goal.get("current_amount", 0)
    target = updated_goal.get("target_amount", 0)
    progress = (current / target * 100) if target > 0 else 0

    type_emoji = {"payoff": "🏍️", "savings": "💰", "purchase": "🛒"}.get(goal.get("goal_type", "savings"), "🎯")

    msg = f"✅ {type_emoji} Paid {format_currency(amount)} to *{goal_name}*\n"
    msg += f"{'█' * int(progress / 10)}{'░' * (10 - int(progress / 10))} {progress:.0f}%\n"
    msg += f"{format_currency(current)} / {format_currency(target)}"

    if progress >= 100:
        msg += "\n\n🎉 *GOAL COMPLETE!* 🎉"

    send_message(chat_id, msg)


# ============ PAY PERIOD HANDLERS ============

def handle_payday(chat_id, user_id):
    """Handle payday - start new pay period"""
    user_states[user_id] = "payday"

    current_period = db.get_current_pay_period_sync(user_id)
    if current_period:
        msg = "💵 *Payday!*\n\n"
        msg += f"Previous period: {current_period['period_start']} to {current_period['period_end']}\n\n"
        msg += "Enter your actual income received:\n"
        msg += "Example: `33040`"
    else:
        msg = "💵 *Start Your First Pay Period*\n\n"
        msg += "Enter: `income start_date`\n"
        msg += "Example: `33040 2024-01-15`\n\n"
        msg += "(Date format: YYYY-MM-DD)"

    send_message(chat_id, msg)


# ============ DASHBOARD HANDLER ============

def handle_dashboard(chat_id, user_id, username):
    """Show comprehensive financial dashboard"""
    user = get_or_create_user(user_id, username)
    accounts = db.get_bank_accounts_sync(user_id)
    cards = db.get_credit_cards_sync(user_id)
    goals = db.get_goals_sync(user_id)
    bills = db.get_bills_sync(user_id)
    current_period = db.get_current_pay_period_sync(user_id)

    now = datetime.now()

    msg = "┌─────────────────────────────────┐\n"
    msg += "│ 💰 *FINANCIAL DASHBOARD*        │\n"
    msg += "├─────────────────────────────────┤\n"

    # Bank Accounts Section
    msg += "│ 🏦 *BANK ACCOUNTS*              │\n"
    if accounts:
        total_bank = 0
        for a in accounts:
            balance = a.get("current_balance", 0)
            total_bank += balance
            purpose = f" ({a.get('purpose', '')})" if a.get('purpose') else ""
            msg += f"│   {a['bank_name']}: {format_currency(balance)}{purpose}\n"
        msg += f"│   *Total:* {format_currency(total_bank)}\n"
    else:
        msg += "│   No accounts set up\n"

    msg += "├─────────────────────────────────┤\n"

    # Credit Cards Section
    msg += "│ 💳 *CREDIT CARDS*               │\n"
    if cards:
        for c in cards:
            balance = c.get("current_balance", 0)
            limit = c.get("credit_limit", 0)
            util = int(balance / limit * 100) if limit > 0 else 0
            msg += f"│   {c['card_name']}: {format_currency(balance)} / {format_currency(limit)} ({util}%)\n"
    else:
        msg += "│   No cards set up\n"

    msg += "├─────────────────────────────────┤\n"

    # Pay Period Section
    msg += "│ 📅 *PAY PERIOD*                 │\n"
    if current_period:
        try:
            start = datetime.strptime(str(current_period['period_start']), "%Y-%m-%d")
            end = datetime.strptime(str(current_period['period_end']), "%Y-%m-%d")
            total_days = (end - start).days
            current_day = (now - start).days + 1
            days_left = max((end - now).days, 0)
            msg += f"│   Day {current_day} of {total_days} | {days_left} days left\n"

            income = current_period.get("actual_income") or current_period.get("expected_income") or 0
            if income > 0 and days_left > 0:
                daily = income / total_days
                msg += f"│   Daily limit: {format_currency(daily)}\n"
        except Exception:
            msg += "│   Period active\n"
    else:
        msg += "│   No active period. Use /payday\n"

    msg += "├─────────────────────────────────┤\n"

    # Payoff Goals Section
    payoff_goals = [g for g in goals if g.get("goal_type") == "payoff"]
    if payoff_goals:
        for g in payoff_goals:
            current = g.get("current_amount", 0)
            target = g.get("target_amount", 0)
            progress = int(current / target * 100) if target > 0 else 0
            bars = "█" * (progress // 10) + "░" * (10 - progress // 10)
            msg += f"│ 🏍️ *{g['name'].upper()} PAYOFF*\n"
            msg += f"│   {bars} {progress}%\n"
            msg += f"│   {format_currency(current)} / {format_currency(target)}\n"
            if g.get("target_date"):
                msg += f"│   Target: {g['target_date']}\n"

        msg += "├─────────────────────────────────┤\n"

    # Upcoming Bills Section
    msg += "│ 📋 *UPCOMING BILLS*             │\n"
    if bills:
        today = now.day
        for b in sorted(bills, key=lambda x: x.get("due_date", 31)):
            due = b.get("due_date", 0)
            days_until = due - today if due >= today else (30 - today) + due
            if days_until <= 3:
                indicator = "🔴"
            elif days_until <= 7:
                indicator = "🟡"
            else:
                indicator = "🟢"
            msg += f"│   {indicator} {b['name']} ({due}th) - {days_until} days\n"
    else:
        msg += "│   No bills set up\n"

    msg += "└─────────────────────────────────┘"

    send_message(chat_id, msg)


def handle_bills(chat_id, user_id):
    """Show upcoming bills with due dates"""
    bills = db.get_bills_sync(user_id)

    if not bills:
        send_message(chat_id, "📋 No bills set up yet.\n\nUse /setup → Set Fixed Bills to add some!")
        return

    now = datetime.now()
    today = now.day

    msg = "📋 *Upcoming Bills*\n\n"
    total = 0

    for b in sorted(bills, key=lambda x: x.get("due_date", 31)):
        due = b.get("due_date", 0)
        amount = b.get("amount", 0)
        total += amount

        days_until = due - today if due >= today else (30 - today) + due

        if days_until == 0:
            indicator = "🔴 *TODAY*"
        elif days_until == 1:
            indicator = "🔴 Tomorrow"
        elif days_until <= 3:
            indicator = f"🔴 {days_until} days"
        elif days_until <= 7:
            indicator = f"🟡 {days_until} days"
        else:
            indicator = f"🟢 {days_until} days"

        msg += f"*{b['name']}* - {format_currency(amount)}\n"
        msg += f"   Due: {due}th | {indicator}\n\n"

    msg += f"━━━━━━━━━━━━━━━━━━━━\n📋 *Total Monthly Bills:* {format_currency(total)}"

    send_message(chat_id, msg)


def handle_rebalance(chat_id, user_id, username):
    """Recalculate goal contributions based on available budget"""
    user = get_or_create_user(user_id, username)
    goals = db.get_goals_sync(user_id)
    bills = db.get_bills_sync(user_id)

    if not goals:
        send_message(chat_id, "❌ No goals to rebalance. Use /addgoal first.")
        return

    income = user.get("monthly_income", 0)
    extra_pct = user.get("extra_pct", 25)
    total_bills = sum(b.get("amount", 0) for b in bills)

    calc = GoalCalculator(income, total_bills, extra_pct)
    result = calc.calculate_contributions(goals)

    msg = "🔄 *Goal Rebalance*\n\n"
    msg += f"Monthly extra budget: {format_currency(result['extra_pool'])}\n\n"

    for allocation in result["allocations"]:
        msg += f"*{allocation['name']}* (P{allocation['priority']})\n"
        msg += f"   Suggested: {format_currency(allocation['monthly'])}/month\n"
        msg += f"   Months to goal: {allocation['months_to_goal']:.1f}\n\n"

    if result["unallocated"] > 0:
        msg += f"Unallocated: {format_currency(result['unallocated'])}\n"

    if result["warning"]:
        msg += f"\n⚠️ {result['warning']}"

    send_message(chat_id, msg)


def handle_simulate(chat_id, user_id, username):
    """Start simulation mode"""
    user_states[user_id] = "simulate"
    send_message(
        chat_id,
        "🔮 *Simulate New Goal*\n\n"
        "Enter the goal you want to simulate:\n"
        "`name amount target_date`\n\n"
        "Example: `iphone 70000 2024-12-01`\n\n"
        "This shows impact without committing."
    )


def handle_callback(callback_id, chat_id, message_id, user_id, data):
    """Handle callback button presses"""
    answer_callback(callback_id)

    if data == "setup_income":
        user_states[user_id] = "income"
        edit_message(
            chat_id, message_id,
            "💰 *Set Your Monthly Income*\n\n"
            "Enter your total monthly income in PHP:\n"
            "Example: `83000`\n\n"
            "Or if you earn in USD, type like: `$7/hr 176hrs`"
        )

    elif data == "setup_bills":
        user_states[user_id] = "bills"
        edit_message(
            chat_id, message_id,
            "📋 *Set Your Fixed Monthly Bills*\n\n"
            "Enter each bill on a new line:\n"
            "`bill_name amount due_date`\n\n"
            "Example:\n"
            "```\n"
            "motorcycle 6500 7\n"
            "insurance 2500 30\n"
            "power 2000 28\n"
            "```"
        )

    elif data == "setup_budget":
        user_states[user_id] = "budget"
        edit_message(
            chat_id, message_id,
            "📊 *Set Your Budget Split*\n\n"
            "Enter percentages for each category (must total 100):\n"
            "`needs wants savings extra`\n\n"
            "Example: `40 20 15 25`\n\n"
            "• Needs = Food, transport, essentials\n"
            "• Wants = Entertainment, shopping\n"
            "• Savings = Emergency fund\n"
            "• Extra = Debt payoff / goals"
        )

    elif data == "setup_view":
        user_data = db.get_user_sync(user_id)
        bills = db.get_bills_sync(user_id)
        accounts = db.get_bank_accounts_sync(user_id)
        cards = db.get_credit_cards_sync(user_id)
        goals = db.get_goals_sync(user_id)

        bills_text = "\n".join([f"  • {b['name']}: {format_currency(b['amount'])} (due: {b['due_date']}th)" for b in bills]) or "  None set"
        accounts_text = "\n".join([f"  • {a['bank_name']}: {format_currency(a.get('current_balance', 0))}" for a in accounts]) or "  None set"
        cards_text = "\n".join([f"  • {c['card_name']}: {format_currency(c.get('current_balance', 0))}/{format_currency(c.get('credit_limit', 0))}" for c in cards]) or "  None set"
        goals_text = "\n".join([f"  • {g['name']}: {format_currency(g.get('current_amount', 0))}/{format_currency(g.get('target_amount', 0))}" for g in goals]) or "  None set"

        edit_message(
            chat_id, message_id,
            f"📋 *Your Current Setup*\n\n"
            f"💰 *Monthly Income:* {format_currency(user_data.get('monthly_income', 0) if user_data else 0)}\n\n"
            f"📋 *Fixed Bills:*\n{bills_text}\n\n"
            f"🏦 *Bank Accounts:*\n{accounts_text}\n\n"
            f"💳 *Credit Cards:*\n{cards_text}\n\n"
            f"🎯 *Goals:*\n{goals_text}\n\n"
            f"📊 *Budget Split:*\n"
            f"  • Needs: {user_data.get('needs_pct', 40) if user_data else 40}%\n"
            f"  • Wants: {user_data.get('wants_pct', 20) if user_data else 20}%\n"
            f"  • Savings: {user_data.get('savings_pct', 15) if user_data else 15}%\n"
            f"  • Extra: {user_data.get('extra_pct', 25) if user_data else 25}%\n\n"
            f"Use /setup to modify these settings."
        )


def handle_message(chat_id, user_id, text):
    """Handle text messages"""
    original_text = text.strip()
    text = original_text.lower()

    # Check setup wizard state
    state = user_states.get(user_id)

    if state == "income":
        try:
            if "$" in text and "/hr" in text:
                parts = text.replace("$", "").replace("/hr", "").replace("hrs", "").split()
                hourly = float(parts[0])
                hours = float(parts[1])
                income = hourly * hours * 59
            else:
                income = float(text.replace(",", "").replace("₱", ""))

            db.update_user_sync(user_id, {"monthly_income": income})
            user_states.pop(user_id, None)

            send_message(chat_id, f"✅ Monthly income set to {format_currency(income)}")
            return
        except Exception as e:
            logger.error(f"Income parse error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    elif state == "bills":
        try:
            lines = text.strip().split("\n")
            count = 0
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 3:
                    name = parts[0]
                    amount = float(parts[1])
                    due_date = int(parts[2])
                    db.add_bill_sync(user_id, name, amount, due_date)
                    count += 1

            user_states.pop(user_id, None)
            send_message(chat_id, f"✅ Added {count} bill(s)!")
            return
        except Exception as e:
            logger.error(f"Bills parse error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    elif state == "budget":
        try:
            parts = text.split()
            if len(parts) == 4:
                needs, wants, savings, extra = map(int, parts)
                if needs + wants + savings + extra == 100:
                    db.update_user_sync(user_id, {
                        "needs_pct": needs,
                        "wants_pct": wants,
                        "savings_pct": savings,
                        "extra_pct": extra
                    })
                    user_states.pop(user_id, None)
                    send_message(chat_id, "✅ Budget split updated!")
                    return
            send_message(chat_id, "❌ Must add up to 100%")
            return
        except:
            send_message(chat_id, "❌ Invalid format.")
            return

    # Handle new states
    elif state == "addbank":
        try:
            parts = original_text.split()
            if len(parts) >= 2:
                bank_name = parts[0]
                balance = float(parts[1]) if len(parts) > 1 else 0
                purpose = parts[2] if len(parts) > 2 else None
                if purpose and purpose not in ['savings', 'spending', 'allowance', 'emergency']:
                    purpose = None
                db.add_bank_account_sync(user_id, bank_name, balance, purpose)
                user_states.pop(user_id, None)
                send_message(chat_id, f"✅ Added *{bank_name}* with balance {format_currency(balance)}")
                return
            send_message(chat_id, "❌ Invalid format. Try: `BankName 1000 savings`")
            return
        except Exception as e:
            logger.error(f"Add bank error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    elif state == "deposit":
        try:
            parts = original_text.split()
            if len(parts) >= 2:
                amount = float(parts[0].replace(",", "").replace("₱", ""))
                bank_name = parts[1]
                handle_deposit(chat_id, user_id, bank_name, amount)
                user_states.pop(user_id, None)
                return
            send_message(chat_id, "❌ Invalid format. Try: `5000 BPI`")
            return
        except Exception as e:
            logger.error(f"Deposit error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    elif state == "withdraw":
        try:
            parts = original_text.split()
            if len(parts) >= 2:
                amount = float(parts[0].replace(",", "").replace("₱", ""))
                bank_name = parts[1]
                handle_withdraw(chat_id, user_id, bank_name, amount)
                user_states.pop(user_id, None)
                return
            send_message(chat_id, "❌ Invalid format. Try: `1000 UnionBank`")
            return
        except Exception as e:
            logger.error(f"Withdraw error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    elif state == "transfer":
        try:
            parts = original_text.split()
            if len(parts) >= 3:
                from_bank = parts[0]
                to_bank = parts[1]
                amount = float(parts[2].replace(",", "").replace("₱", ""))

                from_account = db.get_bank_account_by_name_sync(user_id, from_bank)
                to_account = db.get_bank_account_by_name_sync(user_id, to_bank)

                if not from_account:
                    send_message(chat_id, f"❌ Bank '{from_bank}' not found.")
                    return
                if not to_account:
                    send_message(chat_id, f"❌ Bank '{to_bank}' not found.")
                    return
                if from_account["current_balance"] < amount:
                    send_message(chat_id, f"❌ Insufficient balance in {from_bank}.")
                    return

                # Perform transfer
                new_from = from_account["current_balance"] - amount
                new_to = to_account["current_balance"] + amount
                db.update_bank_balance_sync(from_account["id"], new_from)
                db.update_bank_balance_sync(to_account["id"], new_to)
                db.add_transaction_sync(user_id, "bank", from_account["id"], "transfer", -amount, f"Transfer to {to_bank}")
                db.add_transaction_sync(user_id, "bank", to_account["id"], "transfer", amount, f"Transfer from {from_bank}")

                user_states.pop(user_id, None)
                send_message(
                    chat_id,
                    f"✅ Transferred {format_currency(amount)}\n"
                    f"From: *{from_account['bank_name']}* → {format_currency(new_from)}\n"
                    f"To: *{to_account['bank_name']}* → {format_currency(new_to)}"
                )
                return
            send_message(chat_id, "❌ Invalid format. Try: `BPI UnionBank 5000`")
            return
        except Exception as e:
            logger.error(f"Transfer error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    elif state == "addcc":
        try:
            parts = original_text.split()
            if len(parts) >= 2:
                card_name = parts[0]
                limit = float(parts[1])
                due_date = int(parts[2]) if len(parts) > 2 else None
                db.add_credit_card_sync(user_id, card_name, limit, due_date)
                user_states.pop(user_id, None)
                send_message(chat_id, f"✅ Added *{card_name}* with limit {format_currency(limit)}")
                return
            send_message(chat_id, "❌ Invalid format. Try: `BDO 50000 15`")
            return
        except Exception as e:
            logger.error(f"Add CC error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    elif state == "ccpay":
        try:
            parts = original_text.split()
            if len(parts) >= 2:
                card_name = parts[0]
                amount = float(parts[1].replace(",", "").replace("₱", ""))

                card = db.get_credit_card_by_name_sync(user_id, card_name)
                if card:
                    new_balance = max(0, card["current_balance"] - amount)
                    db.update_credit_card_balance_sync(card["id"], new_balance)
                    db.add_transaction_sync(user_id, "credit_card", card["id"], "payment", amount, f"Payment to {card_name}")
                    user_states.pop(user_id, None)
                    send_message(
                        chat_id,
                        f"✅ Paid {format_currency(amount)} to *{card['card_name']}*\n"
                        f"New balance: {format_currency(new_balance)}"
                    )
                else:
                    send_message(chat_id, f"❌ Card '{card_name}' not found.")
                return
            send_message(chat_id, "❌ Invalid format. Try: `BDO 5000`")
            return
        except Exception as e:
            logger.error(f"CC pay error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    elif state == "addgoal":
        try:
            parts = original_text.split()
            if len(parts) >= 3:
                name = parts[0]
                goal_type = parts[1] if parts[1] in ['payoff', 'savings', 'purchase'] else 'savings'
                target = float(parts[2] if parts[1] in ['payoff', 'savings', 'purchase'] else parts[1])
                monthly = float(parts[3]) if len(parts) > 3 else 0
                target_date = parts[4] if len(parts) > 4 else None

                db.add_goal_sync(user_id, name, goal_type, target, monthly, 1, target_date)
                user_states.pop(user_id, None)
                send_message(
                    chat_id,
                    f"✅ Added goal *{name}*\n"
                    f"Type: {goal_type}\n"
                    f"Target: {format_currency(target)}\n"
                    f"Monthly: {format_currency(monthly)}"
                )
                return
            send_message(chat_id, "❌ Invalid format. Try: `motorcycle payoff 208000 6500 2024-09-01`")
            return
        except Exception as e:
            logger.error(f"Add goal error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    elif state == "payday":
        try:
            parts = original_text.split()
            income = float(parts[0].replace(",", "").replace("₱", ""))

            current_period = db.get_current_pay_period_sync(user_id)
            if current_period:
                # Close old period
                db.close_pay_period_sync(current_period["id"])
                # Calculate new period (14 days from old end)
                old_end = datetime.strptime(str(current_period["period_end"]), "%Y-%m-%d")
                new_start = old_end + timedelta(days=1)
                new_end = new_start + timedelta(days=13)
            else:
                # First period - use provided date or today
                if len(parts) > 1:
                    new_start = datetime.strptime(parts[1], "%Y-%m-%d")
                else:
                    new_start = datetime.now()
                new_end = new_start + timedelta(days=13)

            db.create_pay_period_sync(
                user_id,
                new_start.strftime("%Y-%m-%d"),
                new_end.strftime("%Y-%m-%d"),
                expected_income=income,
                actual_income=income
            )

            user_states.pop(user_id, None)
            daily = income / 14
            send_message(
                chat_id,
                f"💵 *Payday Logged!*\n\n"
                f"Income: {format_currency(income)}\n"
                f"Period: {new_start.strftime('%b %d')} - {new_end.strftime('%b %d')}\n"
                f"Daily limit: {format_currency(daily)}"
            )
            return
        except Exception as e:
            logger.error(f"Payday error: {e}")
            send_message(chat_id, "❌ Invalid format. Try: `33040` or `33040 2024-01-15`")
            return

    elif state == "simulate":
        try:
            parts = original_text.split()
            if len(parts) >= 2:
                name = parts[0]
                amount = float(parts[1])
                target_date = parts[2] if len(parts) > 2 else None

                user = db.get_user_sync(user_id)
                goals = db.get_goals_sync(user_id)
                bills = db.get_bills_sync(user_id)

                income = user.get("monthly_income", 0) if user else 0
                extra_pct = user.get("extra_pct", 25) if user else 25
                total_bills = sum(b.get("amount", 0) for b in bills)

                calc = GoalCalculator(income, total_bills, extra_pct)

                # Add simulated goal
                sim_goal = {
                    "name": name,
                    "goal_type": "purchase",
                    "target_amount": amount,
                    "current_amount": 0,
                    "monthly_contribution": 0,
                    "priority": len(goals) + 1,
                    "target_date": target_date
                }
                all_goals = goals + [sim_goal]

                result = calc.calculate_contributions(all_goals)

                msg = f"🔮 *Simulation: Adding {name}*\n\n"
                msg += f"Target: {format_currency(amount)}\n\n"
                msg += "*Impact on existing goals:*\n"

                for alloc in result["allocations"]:
                    if alloc["name"] == name:
                        msg += f"\n📍 *{alloc['name']}* (NEW)\n"
                    else:
                        msg += f"\n*{alloc['name']}*\n"
                    msg += f"   Monthly: {format_currency(alloc['monthly'])}\n"
                    msg += f"   Time to goal: {alloc['months_to_goal']:.1f} months\n"

                if result["warning"]:
                    msg += f"\n⚠️ {result['warning']}"

                msg += "\n\nUse /addgoal to add this goal."
                user_states.pop(user_id, None)
                send_message(chat_id, msg)
                return
            send_message(chat_id, "❌ Invalid format. Try: `iphone 70000 2024-12-01`")
            return
        except Exception as e:
            logger.error(f"Simulate error: {e}")
            send_message(chat_id, "❌ Invalid format. Try again.")
            return

    # ============ INLINE PARSING ============

    parts = text.split()

    # Pattern: cc <amount> <description> - Credit card spend
    if len(parts) >= 2 and parts[0] == "cc":
        try:
            amount = float(parts[1].replace(",", "").replace("₱", ""))
            description = " ".join(parts[2:]) if len(parts) > 2 else ""
            handle_ccspend(chat_id, user_id, None, amount, description)
            return
        except ValueError:
            pass

    # Pattern: deposit <amount> <bank> - Bank deposit
    if len(parts) >= 3 and parts[0] == "deposit":
        try:
            amount = float(parts[1].replace(",", "").replace("₱", ""))
            bank_name = parts[2]
            handle_deposit(chat_id, user_id, bank_name, amount)
            return
        except ValueError:
            pass

    # Pattern: withdraw <amount> <bank> - Bank withdrawal
    if len(parts) >= 3 and parts[0] == "withdraw":
        try:
            amount = float(parts[1].replace(",", "").replace("₱", ""))
            bank_name = parts[2]
            handle_withdraw(chat_id, user_id, bank_name, amount)
            return
        except ValueError:
            pass

    # Pattern: paid <goal_name> [amount] - Pay to goal
    if len(parts) >= 2 and parts[0] == "paid":
        goal_name = parts[1]
        amount = None
        if len(parts) >= 3:
            try:
                amount = float(parts[2].replace(",", "").replace("₱", ""))
            except ValueError:
                pass
        handle_paid_goal(chat_id, user_id, goal_name, amount)
        return

    # Original expense parsing: <description> <amount> <category>
    if len(parts) >= 3:
        category = parts[-1]

        # Check if valid category
        if category in ["needs", "wants", "savings"]:
            try:
                amount = float(parts[-2].replace(",", "").replace("₱", ""))
                description = " ".join(parts[:-2])

                # Add the expense
                db.add_expense_sync(user_id, description, amount, category)
                logger.info(f"Added expense: {description} {amount} {category} for user {user_id}")

                # Try to get budget status for response
                try:
                    user = db.get_user_sync(user_id)
                    now = datetime.now()
                    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    expenses = db.get_expenses_sync(user_id, month_start)

                    income = user.get("monthly_income", 0) if user else 0
                    bills_list = db.get_bills_sync(user_id)
                    total_bills = sum(b["amount"] for b in bills_list)
                    available = income - total_bills

                    if category == "needs":
                        budget = available * (user.get("needs_pct", 40) if user else 40) / 100
                        spent = sum(e["amount"] for e in expenses if e["category"] == "needs")
                    elif category == "wants":
                        budget = available * (user.get("wants_pct", 20) if user else 20) / 100
                        spent = sum(e["amount"] for e in expenses if e["category"] == "wants")
                    else:
                        budget = available * (user.get("savings_pct", 15) if user else 15) / 100
                        spent = sum(e["amount"] for e in expenses if e["category"] == "savings")

                    remaining = budget - spent
                    pct = (spent / budget * 100) if budget > 0 else 0

                    emoji = {"needs": "🍽️", "wants": "🎮", "savings": "💰"}[category]

                    response = f"✅ {emoji} {description.title()}: {format_currency(amount)}\n"
                    response += f"{get_progress_bar(pct)} {pct:.0f}%\n"
                    response += f"Remaining: {format_currency(remaining)}"

                    if pct >= 90:
                        response += "\n🚨 *Budget almost gone!*"

                    send_message(chat_id, response)
                except Exception as e:
                    # Budget calculation failed, but expense was added
                    logger.error(f"Budget calc error: {e}")
                    emoji = {"needs": "🍽️", "wants": "🎮", "savings": "💰"}[category]
                    send_message(chat_id, f"✅ {emoji} {description.title()}: {format_currency(amount)} logged!")

                return

            except ValueError as e:
                logger.error(f"Expense parse error: {e} for text: {text}")
                # Fall through to help message

    send_message(
        chat_id,
        "💡 *Quick commands:*\n"
        "• Expense: `lunch 150 needs`\n"
        "• Credit card: `cc 500 shoes`\n"
        "• Deposit: `deposit 5000 bpi`\n"
        "• Withdraw: `withdraw 1000 unionbank`\n"
        "• Pay goal: `paid motorcycle 6500`"
    )


# ============ FLASK ROUTES ============

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming webhook from Telegram"""
    try:
        data = request.get_json()

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            user_id = message["from"]["id"]
            first_name = message["from"].get("first_name", "")
            username = message["from"].get("username", "")

            if "text" in message:
                text = message["text"]

                # Core commands
                if text == "/start":
                    handle_start(chat_id, user_id, first_name, username)
                elif text == "/setup":
                    handle_setup(chat_id, user_id, username)
                elif text == "/status":
                    handle_status(chat_id, user_id, username)
                elif text == "/history":
                    handle_history(chat_id, user_id)
                elif text == "/summary":
                    handle_summary(chat_id, user_id)
                elif text == "/help":
                    handle_help(chat_id)

                # Bank account commands
                elif text == "/banks":
                    handle_banks(chat_id, user_id)
                elif text == "/addbank":
                    handle_addbank(chat_id, user_id)
                elif text == "/deposit":
                    handle_deposit(chat_id, user_id)
                elif text == "/withdraw":
                    handle_withdraw(chat_id, user_id)
                elif text == "/transfer":
                    handle_transfer(chat_id, user_id)

                # Credit card commands
                elif text == "/cc":
                    handle_cc(chat_id, user_id)
                elif text == "/addcc":
                    handle_addcc(chat_id, user_id)
                elif text == "/ccpay":
                    handle_ccpay(chat_id, user_id)

                # Goal commands
                elif text == "/goals":
                    handle_goals(chat_id, user_id)
                elif text == "/payoff":
                    handle_payoff(chat_id, user_id)
                elif text == "/addgoal":
                    handle_addgoal(chat_id, user_id)
                elif text == "/rebalance":
                    handle_rebalance(chat_id, user_id, username)
                elif text == "/simulate":
                    handle_simulate(chat_id, user_id, username)

                # Pay period commands
                elif text == "/payday":
                    handle_payday(chat_id, user_id)

                # Dashboard & reports
                elif text == "/dashboard":
                    handle_dashboard(chat_id, user_id, username)
                elif text == "/bills":
                    handle_bills(chat_id, user_id)

                # Handle non-command messages
                elif not text.startswith("/"):
                    handle_message(chat_id, user_id, text)

        elif "callback_query" in data:
            callback = data["callback_query"]
            callback_id = callback["id"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]
            user_id = callback["from"]["id"]
            callback_data = callback["data"]

            handle_callback(callback_id, chat_id, message_id, user_id, callback_data)

        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)})


@flask_app.route("/")
def index():
    """Health check"""
    return "AvecBanker Bot is running! 🏦"


@flask_app.route("/set_webhook")
def set_webhook():
    """Set the webhook URL"""
    try:
        response = requests.post(
            f"{API_URL}/setWebhook",
            json={"url": WEBHOOK_URL},
            timeout=10
        )
        return f"Webhook set to {WEBHOOK_URL}\n\nResponse: {response.json()}"
    except Exception as e:
        return f"Error setting webhook: {e}"


# For local testing
if __name__ == "__main__":
    flask_app.run(debug=True, port=5000)
