"""
Notification Worker for AvecBanker Bot
Run via PythonAnywhere scheduled task every few hours

Checks for:
- Bills due in 3 days, 1 day, today
- Budget warnings (>80% spent)
- Weekly summaries (Sundays)
- Payoff milestone celebrations
"""

import os
import logging
import requests
from datetime import datetime, date
from database import Database

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize
db = Database()

# Bot token
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id: int, text: str, parse_mode: str = "Markdown"):
    """Send a message via Telegram API"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }

    try:
        response = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        result = response.json()
        if not result.get("ok"):
            logger.error(f"Send message failed: {result}")
        return result
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None


def format_currency(amount: float) -> str:
    """Format number as Philippine Peso"""
    return f"₱{amount:,.2f}"


def check_bill_reminders():
    """Check all users for upcoming bill due dates"""
    logger.info("Checking bill reminders...")
    users = db.get_all_users_sync()

    for user in users:
        telegram_id = user.get("telegram_id")
        if not user.get("reminders_enabled", True):
            continue

        bills = db.get_bills_sync(telegram_id)
        if not bills:
            continue

        today = date.today().day
        upcoming = []

        for bill in bills:
            due_date = bill.get("due_date", 0)
            name = bill.get("name", "Unknown")
            amount = bill.get("amount", 0)

            # Calculate days until due
            if due_date >= today:
                days_until = due_date - today
            else:
                # Bill is next month
                days_until = (30 - today) + due_date

            if days_until == 0:
                upcoming.append({
                    "name": name,
                    "amount": amount,
                    "urgency": "today",
                    "message": f"🔴 *{name}* - {format_currency(amount)} - *DUE TODAY!*"
                })
            elif days_until == 1:
                upcoming.append({
                    "name": name,
                    "amount": amount,
                    "urgency": "tomorrow",
                    "message": f"🟠 *{name}* - {format_currency(amount)} - Due tomorrow"
                })
            elif days_until <= 3:
                upcoming.append({
                    "name": name,
                    "amount": amount,
                    "urgency": "soon",
                    "message": f"🟡 *{name}* - {format_currency(amount)} - Due in {days_until} days"
                })

        if upcoming:
            msg = "📋 *Bill Reminder*\n\n"
            for bill in sorted(upcoming, key=lambda x: {"today": 0, "tomorrow": 1, "soon": 2}.get(x["urgency"], 3)):
                msg += bill["message"] + "\n"

            # Add total if multiple bills
            if len(upcoming) > 1:
                total = sum(b["amount"] for b in upcoming)
                msg += f"\n💰 *Total due:* {format_currency(total)}"

            send_message(telegram_id, msg)
            logger.info(f"Sent bill reminder to user {telegram_id}: {len(upcoming)} bills")


def check_budget_warnings():
    """Check all users for budget overspending warnings"""
    logger.info("Checking budget warnings...")
    users = db.get_all_users_sync()

    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for user in users:
        telegram_id = user.get("telegram_id")
        if not user.get("reminders_enabled", True):
            continue

        income = user.get("monthly_income", 0)
        if income <= 0:
            continue

        bills = db.get_bills_sync(telegram_id)
        expenses = db.get_expenses_sync(telegram_id, month_start)

        total_bills = sum(b.get("amount", 0) for b in bills)
        available = income - total_bills

        warnings = []

        # Check each category
        for category, pct_key, emoji in [
            ("needs", "needs_pct", "🍽️"),
            ("wants", "wants_pct", "🎮"),
            ("savings", "savings_pct", "💰")
        ]:
            budget = available * (user.get(pct_key, 40 if category == "needs" else 20) / 100)
            spent = sum(e.get("amount", 0) for e in expenses if e.get("category") == category)

            if budget > 0:
                pct = (spent / budget) * 100
                if pct >= 90:
                    warnings.append({
                        "category": category,
                        "emoji": emoji,
                        "spent": spent,
                        "budget": budget,
                        "pct": pct,
                        "severity": "critical" if pct >= 100 else "warning"
                    })

        if warnings:
            msg = "🚨 *Budget Warning*\n\n"
            for w in warnings:
                if w["severity"] == "critical":
                    msg += f"{w['emoji']} *{w['category'].upper()}* - OVER BUDGET!\n"
                else:
                    msg += f"{w['emoji']} *{w['category'].upper()}* - {w['pct']:.0f}% used\n"
                msg += f"   {format_currency(w['spent'])} / {format_currency(w['budget'])}\n\n"

            send_message(telegram_id, msg)
            logger.info(f"Sent budget warning to user {telegram_id}: {len(warnings)} categories")


def check_payoff_milestones():
    """Check for payoff goal milestones (25%, 50%, 75%, 100%)"""
    logger.info("Checking payoff milestones...")
    users = db.get_all_users_sync()

    milestones = [25, 50, 75, 100]

    for user in users:
        telegram_id = user.get("telegram_id")
        goals = db.get_goals_sync(telegram_id)

        for goal in goals:
            if goal.get("goal_type") != "payoff":
                continue

            target = goal.get("target_amount", 0)
            current = goal.get("current_amount", 0)

            if target <= 0:
                continue

            progress = (current / target) * 100

            for milestone in milestones:
                # Check if we just crossed this milestone
                # (would need to track last notified milestone in DB for production)
                if milestone - 5 <= progress < milestone + 5:
                    if milestone == 100:
                        msg = f"🎉🎉🎉 *GOAL COMPLETE!* 🎉🎉🎉\n\n"
                        msg += f"*{goal['name']}* is fully paid off!\n"
                        msg += f"Total: {format_currency(current)}\n\n"
                        msg += "Congratulations! Time to celebrate! 🎊"
                    else:
                        emoji = "🏍️" if "motorcycle" in goal["name"].lower() else "🎯"
                        msg = f"{emoji} *{goal['name']} Milestone!*\n\n"
                        msg += f"You've reached {milestone}% of your goal!\n"
                        msg += f"Progress: {format_currency(current)} / {format_currency(target)}\n"
                        remaining = target - current
                        msg += f"Remaining: {format_currency(remaining)}\n\n"
                        msg += "Keep going! 💪"

                    # Note: In production, track which milestones were already notified
                    # to avoid duplicate notifications
                    # send_message(telegram_id, msg)
                    logger.info(f"Milestone {milestone}% for goal {goal['name']} (user {telegram_id})")
                    break


def send_weekly_summary():
    """Send weekly summary every Sunday"""
    logger.info("Checking if weekly summary needed...")

    # Only run on Sundays
    if datetime.now().weekday() != 6:
        logger.info("Not Sunday, skipping weekly summary")
        return

    # Only run in the morning (8-10 AM)
    hour = datetime.now().hour
    if hour < 8 or hour > 10:
        logger.info("Not morning hours, skipping weekly summary")
        return

    users = db.get_all_users_sync()

    for user in users:
        telegram_id = user.get("telegram_id")
        if not user.get("reminders_enabled", True):
            continue

        # Get this week's expenses
        now = datetime.now()
        week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = week_start.replace(day=now.day - now.weekday())

        expenses = db.get_expenses_sync(telegram_id, week_start)
        goals = db.get_goals_sync(telegram_id)

        if not expenses and not goals:
            continue

        msg = "📊 *Weekly Summary*\n\n"

        # Expense summary
        if expenses:
            by_category = {"needs": 0, "wants": 0, "savings": 0}
            for e in expenses:
                cat = e.get("category", "needs")
                by_category[cat] = by_category.get(cat, 0) + e.get("amount", 0)

            total = sum(by_category.values())
            msg += "*This Week's Spending:*\n"
            msg += f"🍽️ Needs: {format_currency(by_category['needs'])}\n"
            msg += f"🎮 Wants: {format_currency(by_category['wants'])}\n"
            msg += f"💰 Saved: {format_currency(by_category['savings'])}\n"
            msg += f"📈 Total: {format_currency(total)}\n\n"

        # Goal progress
        active_goals = [g for g in goals if g.get("is_active", True)]
        if active_goals:
            msg += "*Goal Progress:*\n"
            for g in active_goals:
                current = g.get("current_amount", 0)
                target = g.get("target_amount", 0)
                progress = (current / target * 100) if target > 0 else 0
                msg += f"🎯 {g['name']}: {progress:.0f}%\n"

        msg += "\nHave a great week! 💪"
        send_message(telegram_id, msg)
        logger.info(f"Sent weekly summary to user {telegram_id}")


def check_pay_period_status():
    """Check pay period status and send alerts"""
    logger.info("Checking pay period status...")
    users = db.get_all_users_sync()

    for user in users:
        telegram_id = user.get("telegram_id")
        if not user.get("reminders_enabled", True):
            continue

        period = db.get_current_pay_period_sync(telegram_id)
        if not period:
            continue

        try:
            end_date = datetime.strptime(str(period["period_end"]), "%Y-%m-%d").date()
            today = date.today()
            days_left = (end_date - today).days

            if days_left == 1:
                msg = "📅 *Pay Period Ending Tomorrow!*\n\n"
                msg += f"Period: {period['period_start']} to {period['period_end']}\n"
                msg += f"Income: {format_currency(period.get('actual_income') or period.get('expected_income') or 0)}\n\n"
                msg += "Use /payday when you get paid to start a new period."
                send_message(telegram_id, msg)
                logger.info(f"Sent pay period warning to user {telegram_id}")

        except (ValueError, TypeError) as e:
            logger.error(f"Pay period date parse error: {e}")


def run_all_checks():
    """Run all notification checks"""
    logger.info("Starting notification checks...")

    try:
        check_bill_reminders()
    except Exception as e:
        logger.error(f"Bill reminders error: {e}")

    try:
        check_budget_warnings()
    except Exception as e:
        logger.error(f"Budget warnings error: {e}")

    try:
        check_payoff_milestones()
    except Exception as e:
        logger.error(f"Payoff milestones error: {e}")

    try:
        send_weekly_summary()
    except Exception as e:
        logger.error(f"Weekly summary error: {e}")

    try:
        check_pay_period_status()
    except Exception as e:
        logger.error(f"Pay period status error: {e}")

    logger.info("Notification checks complete!")


if __name__ == "__main__":
    run_all_checks()
