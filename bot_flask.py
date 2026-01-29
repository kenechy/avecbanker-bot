"""
AvecBanker Bot - PythonAnywhere Version
Uses Flask webhook instead of polling for free hosting compatibility
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import asyncio
from database import Database
from config import Config

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize
db = Database()
config = Config()

# Flask app for webhook
flask_app = Flask(__name__)

# Bot token
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # e.g., https://yourusername.pythonanywhere.com/webhook


# ============ HELPER FUNCTIONS ============

def format_currency(amount: float) -> str:
    """Format number as Philippine Peso"""
    return f"₱{amount:,.2f}"


def get_progress_bar(percentage: float, length: int = 10) -> str:
    """Create a visual progress bar"""
    filled = int(percentage / 100 * length)
    empty = length - filled
    if percentage >= 90:
        return "🔴" * filled + "⬜" * empty
    elif percentage >= 70:
        return "🟡" * filled + "⬜" * empty
    else:
        return "🟢" * filled + "⬜" * empty


def get_or_create_user_sync(telegram_id: int, username: str = None) -> dict:
    """Get existing user or create new one (sync version)"""
    user = db.get_user_sync(telegram_id)
    if not user:
        user = db.create_user_sync(telegram_id, username)
    return user


# ============ BOT HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message and setup"""
    user = update.effective_user
    get_or_create_user_sync(user.id, user.username)
    
    welcome_msg = f"""
🏦 *Welcome to AvecBanker Bot!*

Hello {user.first_name}! I'm your personal budget assistant.

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
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")


async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interactive budget setup"""
    user = update.effective_user
    get_or_create_user_sync(user.id, user.username)
    
    keyboard = [
        [InlineKeyboardButton("💰 Set Income", callback_data="setup_income")],
        [InlineKeyboardButton("📋 Set Fixed Bills", callback_data="setup_bills")],
        [InlineKeyboardButton("📊 Set Budget Split", callback_data="setup_budget")],
        [InlineKeyboardButton("✅ View Current Setup", callback_data="setup_view")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ *Budget Setup*\n\nWhat would you like to configure?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setup button callbacks"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if query.data == "setup_income":
        context.user_data["setup_step"] = "income"
        await query.edit_message_text(
            "💰 *Set Your Monthly Income*\n\n"
            "Enter your total monthly income in PHP:\n"
            "Example: `83000`\n\n"
            "Or if you earn in USD, type like: `$7/hr 176hrs`",
            parse_mode="Markdown"
        )
    
    elif query.data == "setup_bills":
        context.user_data["setup_step"] = "bills"
        await query.edit_message_text(
            "📋 *Set Your Fixed Monthly Bills*\n\n"
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
    
    elif query.data == "setup_budget":
        context.user_data["setup_step"] = "budget"
        await query.edit_message_text(
            "📊 *Set Your Budget Split*\n\n"
            "Enter percentages for each category (must total 100):\n"
            "`needs wants savings extra`\n\n"
            "Example: `40 20 15 25`\n\n"
            "• Needs = Food, transport, essentials\n"
            "• Wants = Entertainment, shopping\n"
            "• Savings = Emergency fund\n"
            "• Extra = Debt payoff / goals",
            parse_mode="Markdown"
        )
    
    elif query.data == "setup_view":
        user_data = db.get_user_sync(user_id)
        bills = db.get_bills_sync(user_id)
        
        bills_text = "\n".join([f"  • {b['name']}: {format_currency(b['amount'])} (due: {b['due_date']}th)" for b in bills]) or "  None set"
        
        await query.edit_message_text(
            f"📋 *Your Current Setup*\n\n"
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


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current budget status"""
    user_id = update.effective_user.id
    user = get_or_create_user_sync(user_id, update.effective_user.username)
    
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
    
    await update.message.reply_text(status_msg, parse_mode="Markdown")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent expenses"""
    user_id = update.effective_user.id
    expenses = db.get_recent_expenses_sync(user_id, limit=10)
    
    if not expenses:
        await update.message.reply_text("No expenses recorded yet!")
        return
    
    history_msg = "📜 *Recent Expenses*\n\n"
    
    for e in expenses:
        date = e["created_at"].strftime("%m/%d") if isinstance(e["created_at"], datetime) else str(e["created_at"])[:5]
        category_emoji = {"needs": "🍽️", "wants": "🎮", "savings": "💰"}
        emoji = category_emoji.get(e["category"], "📝")
        history_msg += f"{date} {emoji} {e['description'].title()}: {format_currency(e['amount'])}\n"
    
    await update.message.reply_text(history_msg, parse_mode="Markdown")


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monthly summary"""
    user_id = update.effective_user.id
    
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
    
    await update.message.reply_text(summary_msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense logging from messages"""
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()
    
    if text.startswith("/"):
        return
    
    # Check setup steps
    step = context.user_data.get("setup_step")
    
    if step == "income":
        try:
            if "$" in text and "/hr" in text:
                parts = text.replace("$", "").replace("/hr", "").replace("hrs", "").split()
                hourly = float(parts[0])
                hours = float(parts[1])
                income = hourly * hours * 59
            else:
                income = float(text.replace(",", "").replace("₱", ""))
            
            db.update_user_sync(user_id, {"monthly_income": income})
            context.user_data["setup_step"] = None
            
            await update.message.reply_text(
                f"✅ Monthly income set to {format_currency(income)}",
                parse_mode="Markdown"
            )
            return
        except:
            await update.message.reply_text("❌ Invalid format. Try again.")
            return
    
    elif step == "bills":
        try:
            lines = text.strip().split("\n")
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 3:
                    name = parts[0]
                    amount = float(parts[1])
                    due_date = int(parts[2])
                    db.add_bill_sync(user_id, name, amount, due_date)
            
            context.user_data["setup_step"] = None
            await update.message.reply_text(f"✅ Added {len(lines)} bill(s)!")
            return
        except:
            await update.message.reply_text("❌ Invalid format. Try again.")
            return
    
    elif step == "budget":
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
                    context.user_data["setup_step"] = None
                    await update.message.reply_text(f"✅ Budget split updated!")
                    return
            await update.message.reply_text("❌ Must add up to 100%")
            return
        except:
            await update.message.reply_text("❌ Invalid format.")
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
                
                await update.message.reply_text(response, parse_mode="Markdown")
                return
    except:
        pass
    
    await update.message.reply_text(
        "💡 To log expense, type:\n`description amount category`\n\nExample: `lunch 150 needs`",
        parse_mode="Markdown"
    )


# ============ APPLICATION SETUP ============

# Build application
application = Application.builder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("setup", setup))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("history", history))
application.add_handler(CommandHandler("summary", summary))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CallbackQueryHandler(setup_callback, pattern="^setup_"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ============ FLASK WEBHOOK ============

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming webhook from Telegram"""
    if request.method == "POST":
        update = Update.de_json(request.get_json(), application.bot)
        
        # Process update
        asyncio.run(application.process_update(update))
        
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"})


@flask_app.route("/")
def index():
    """Health check"""
    return "AvecBanker Bot is running! 🏦"


@flask_app.route("/set_webhook")
def set_webhook():
    """Set the webhook URL"""
    bot = Bot(token=BOT_TOKEN)
    webhook_url = WEBHOOK_URL
    
    asyncio.run(bot.set_webhook(url=webhook_url))
    
    return f"Webhook set to {webhook_url}"


# For PythonAnywhere, the flask_app is imported by WSGI
# For local testing:
if __name__ == "__main__":
    flask_app.run(debug=True, port=5000)
