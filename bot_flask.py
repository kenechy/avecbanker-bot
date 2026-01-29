"""
AvecBanker Bot - PythonAnywhere Version
Uses Flask webhook with direct Bot API calls
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
import asyncio
from database import Database

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

# Create bot instance
bot = Bot(token=BOT_TOKEN)

# Simple user state storage (for setup wizard)
user_states = {}


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


# ============ ASYNC HANDLERS ============

async def handle_start(chat_id: int, user_id: int, first_name: str, username: str):
    """Welcome message"""
    get_or_create_user(user_id, username)

    welcome_msg = f"""
🏦 *Welcome to AvecBanker Bot!*

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

Let's take control of your finances! 💪
"""
    await bot.send_message(chat_id=chat_id, text=welcome_msg, parse_mode="Markdown")


async def handle_setup(chat_id: int, user_id: int, username: str):
    """Interactive budget setup"""
    get_or_create_user(user_id, username)

    keyboard = [
        [InlineKeyboardButton("💰 Set Income", callback_data="setup_income")],
        [InlineKeyboardButton("📋 Set Fixed Bills", callback_data="setup_bills")],
        [InlineKeyboardButton("📊 Set Budget Split", callback_data="setup_budget")],
        [InlineKeyboardButton("✅ View Current Setup", callback_data="setup_view")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(
        chat_id=chat_id,
        text="⚙️ *Budget Setup*\n\nWhat would you like to configure?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_status(chat_id: int, user_id: int, username: str):
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

    status_msg = f"""
📊 *Budget Status - {now.strftime('%B %Y')}*

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
📅 {days_remaining} days remaining this month
"""

    if needs_pct >= 90:
        status_msg += "\n🚨 *WARNING: Needs budget almost depleted!*"
    if wants_pct >= 90:
        status_msg += "\n🚨 *WARNING: Wants budget almost depleted!*"

    await bot.send_message(chat_id=chat_id, text=status_msg, parse_mode="Markdown")


async def handle_history(chat_id: int, user_id: int):
    """Show recent expenses"""
    expenses = db.get_recent_expenses_sync(user_id, limit=10)

    if not expenses:
        await bot.send_message(chat_id=chat_id, text="No expenses recorded yet!")
        return

    history_msg = "📜 *Recent Expenses*\n\n"

    for e in expenses:
        date = e["created_at"].strftime("%m/%d") if isinstance(e["created_at"], datetime) else str(e["created_at"])[:5]
        category_emoji = {"needs": "🍽️", "wants": "🎮", "savings": "💰"}
        emoji = category_emoji.get(e["category"], "📝")
        history_msg += f"{date} {emoji} {e['description'].title()}: {format_currency(e['amount'])}\n"

    await bot.send_message(chat_id=chat_id, text=history_msg, parse_mode="Markdown")


async def handle_summary(chat_id: int, user_id: int):
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

    await bot.send_message(chat_id=chat_id, text=summary_msg, parse_mode="Markdown")


async def handle_help(chat_id: int):
    """Show all commands"""
    help_text = """
📖 *AvecBanker Bot Commands*

*Setup:*
/start - Welcome & quick start
/setup - Configure your budget

*Daily Use:*
• Just type: `lunch 150 needs`
/status - Current budget status

*Reports:*
/history - Recent expenses
/summary - Monthly breakdown

*Categories:*
• `needs` - Food, transport, bills
• `wants` - Entertainment, shopping
• `savings` - Money saved
"""
    await bot.send_message(chat_id=chat_id, text=help_text, parse_mode="Markdown")


async def handle_callback(callback_query_id: str, chat_id: int, message_id: int, user_id: int, data: str):
    """Handle callback button presses"""
    await bot.answer_callback_query(callback_query_id)

    if data == "setup_income":
        user_states[user_id] = "income"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="💰 *Set Your Monthly Income*\n\n"
                 "Enter your total monthly income in PHP:\n"
                 "Example: `83000`\n\n"
                 "Or if you earn in USD, type like: `$7/hr 176hrs`",
            parse_mode="Markdown"
        )

    elif data == "setup_bills":
        user_states[user_id] = "bills"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="📋 *Set Your Fixed Monthly Bills*\n\n"
                 "Enter each bill on a new line:\n"
                 "`bill_name amount due_date`\n\n"
                 "Example:\n"
                 "```\n"
                 "motorcycle 6500 7\n"
                 "insurance 2500 30\n"
                 "power 2000 28\n"
                 "```",
            parse_mode="Markdown"
        )

    elif data == "setup_budget":
        user_states[user_id] = "budget"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="📊 *Set Your Budget Split*\n\n"
                 "Enter percentages for each category (must total 100):\n"
                 "`needs wants savings extra`\n\n"
                 "Example: `40 20 15 25`\n\n"
                 "• Needs = Food, transport, essentials\n"
                 "• Wants = Entertainment, shopping\n"
                 "• Savings = Emergency fund\n"
                 "• Extra = Debt payoff / goals",
            parse_mode="Markdown"
        )

    elif data == "setup_view":
        user_data = db.get_user_sync(user_id)
        bills = db.get_bills_sync(user_id)

        bills_text = "\n".join([f"  • {b['name']}: {format_currency(b['amount'])} (due: {b['due_date']}th)" for b in bills]) or "  None set"

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📋 *Your Current Setup*\n\n"
                 f"💰 *Monthly Income:* {format_currency(user_data.get('monthly_income', 0) if user_data else 0)}\n\n"
                 f"📋 *Fixed Bills:*\n{bills_text}\n\n"
                 f"📊 *Budget Split:*\n"
                 f"  • Needs: {user_data.get('needs_pct', 40) if user_data else 40}%\n"
                 f"  • Wants: {user_data.get('wants_pct', 20) if user_data else 20}%\n"
                 f"  • Savings: {user_data.get('savings_pct', 15) if user_data else 15}%\n"
                 f"  • Extra: {user_data.get('extra_pct', 25) if user_data else 25}%\n\n"
                 f"Use /setup to modify these settings.",
            parse_mode="Markdown"
        )


async def handle_message(chat_id: int, user_id: int, text: str):
    """Handle text messages"""
    text = text.strip().lower()

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

            await bot.send_message(
                chat_id=chat_id,
                text=f"✅ Monthly income set to {format_currency(income)}",
                parse_mode="Markdown"
            )
            return
        except:
            await bot.send_message(chat_id=chat_id, text="❌ Invalid format. Try again.")
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
            await bot.send_message(chat_id=chat_id, text=f"✅ Added {count} bill(s)!")
            return
        except:
            await bot.send_message(chat_id=chat_id, text="❌ Invalid format. Try again.")
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
                    await bot.send_message(chat_id=chat_id, text="✅ Budget split updated!")
                    return
            await bot.send_message(chat_id=chat_id, text="❌ Must add up to 100%")
            return
        except:
            await bot.send_message(chat_id=chat_id, text="❌ Invalid format.")
            return

    # Try to parse as expense
    try:
        parts = text.split()
        if len(parts) >= 3:
            category = parts[-1]
            amount = float(parts[-2].replace(",", "").replace("₱", ""))
            description = " ".join(parts[:-2])

            if category in ["needs", "wants", "savings"]:
                db.add_expense_sync(user_id, description, amount, category)

                # Get budget status
                user = db.get_user_sync(user_id)
                now = datetime.now()
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                expenses = db.get_expenses_sync(user_id, month_start)

                income = user.get("monthly_income", 0) if user else 0
                bills = db.get_bills_sync(user_id)
                total_bills = sum(b["amount"] for b in bills)
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

                await bot.send_message(chat_id=chat_id, text=response, parse_mode="Markdown")
                return
    except:
        pass

    await bot.send_message(
        chat_id=chat_id,
        text="💡 To log expense, type:\n`description amount category`\n\nExample: `lunch 150 needs`",
        parse_mode="Markdown"
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

                if text == "/start":
                    asyncio.run(handle_start(chat_id, user_id, first_name, username))
                elif text == "/setup":
                    asyncio.run(handle_setup(chat_id, user_id, username))
                elif text == "/status":
                    asyncio.run(handle_status(chat_id, user_id, username))
                elif text == "/history":
                    asyncio.run(handle_history(chat_id, user_id))
                elif text == "/summary":
                    asyncio.run(handle_summary(chat_id, user_id))
                elif text == "/help":
                    asyncio.run(handle_help(chat_id))
                elif not text.startswith("/"):
                    asyncio.run(handle_message(chat_id, user_id, text))

        elif "callback_query" in data:
            callback = data["callback_query"]
            callback_id = callback["id"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]
            user_id = callback["from"]["id"]
            callback_data = callback["data"]

            asyncio.run(handle_callback(callback_id, chat_id, message_id, user_id, callback_data))

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
    webhook_url = WEBHOOK_URL
    asyncio.run(bot.set_webhook(url=webhook_url))
    return f"Webhook set to {webhook_url}"


# For local testing
if __name__ == "__main__":
    flask_app.run(debug=True, port=5000)
