"""
Database module for AvecBanker Bot
Uses Supabase as the backend - SYNC methods only for PythonAnywhere
"""

import os
from datetime import datetime
from typing import Optional, List, Dict
from supabase import create_client, Client
from dateutil import parser as date_parser


class Database:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set!")

        self.client: Client = create_client(url, key)

    # ============ USER METHODS ============

    def get_user_sync(self, telegram_id: int) -> Optional[Dict]:
        """Get user by Telegram ID"""
        response = self.client.table("users").select("*").eq("telegram_id", telegram_id).execute()
        return response.data[0] if response.data else None

    def create_user_sync(self, telegram_id: int, username: str = None) -> Dict:
        """Create a new user with default settings"""
        user_data = {
            "telegram_id": telegram_id,
            "username": username,
            "monthly_income": 0,
            "needs_pct": 40,
            "wants_pct": 20,
            "savings_pct": 15,
            "extra_pct": 25,
            "reminders_enabled": True,
            "created_at": datetime.utcnow().isoformat()
        }
        response = self.client.table("users").insert(user_data).execute()
        return response.data[0] if response.data else user_data

    def update_user_sync(self, telegram_id: int, data: Dict) -> Dict:
        """Update user settings"""
        response = self.client.table("users").update(data).eq("telegram_id", telegram_id).execute()
        return response.data[0] if response.data else None

    def get_all_users_sync(self) -> List[Dict]:
        """Get all users"""
        response = self.client.table("users").select("*").execute()
        return response.data

    # ============ EXPENSE METHODS ============

    def add_expense_sync(self, telegram_id: int, description: str, amount: float, category: str) -> Dict:
        """Add a new expense"""
        expense_data = {
            "telegram_id": telegram_id,
            "description": description,
            "amount": amount,
            "category": category,
            "created_at": datetime.utcnow().isoformat()
        }
        response = self.client.table("expenses").insert(expense_data).execute()
        return response.data[0] if response.data else expense_data

    def get_expenses_sync(self, telegram_id: int, since: datetime = None) -> List[Dict]:
        """Get expenses for a user, optionally since a date"""
        query = self.client.table("expenses").select("*").eq("telegram_id", telegram_id)

        if since:
            query = query.gte("created_at", since.isoformat())

        response = query.order("created_at", desc=True).execute()

        # Parse dates
        for exp in response.data:
            if isinstance(exp.get("created_at"), str):
                exp["created_at"] = date_parser.parse(exp["created_at"])

        return response.data

    def get_recent_expenses_sync(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Get recent expenses"""
        response = (
            self.client.table("expenses")
            .select("*")
            .eq("telegram_id", telegram_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        # Parse dates
        for exp in response.data:
            if isinstance(exp.get("created_at"), str):
                exp["created_at"] = date_parser.parse(exp["created_at"])

        return response.data

    def delete_expense_sync(self, expense_id: str) -> bool:
        """Delete an expense by ID"""
        response = self.client.table("expenses").delete().eq("id", expense_id).execute()
        return len(response.data) > 0

    # ============ BILLS METHODS ============

    def add_bill_sync(self, telegram_id: int, name: str, amount: float, due_date: int) -> Dict:
        """Add a recurring bill"""
        bill_data = {
            "telegram_id": telegram_id,
            "name": name,
            "amount": amount,
            "due_date": due_date,
            "created_at": datetime.utcnow().isoformat()
        }
        response = self.client.table("bills").insert(bill_data).execute()
        return response.data[0] if response.data else bill_data

    def get_bills_sync(self, telegram_id: int) -> List[Dict]:
        """Get all active bills for a user"""
        response = (
            self.client.table("bills")
            .select("*")
            .eq("telegram_id", telegram_id)
            .eq("is_active", True)
            .order("due_date")
            .execute()
        )
        return response.data

    def delete_bill_sync(self, bill_id: str) -> bool:
        """Soft delete a bill"""
        response = self.client.table("bills").update({"is_active": False}).eq("id", bill_id).execute()
        return len(response.data) > 0

    def get_bill_by_name_sync(self, telegram_id: int, name: str) -> Optional[Dict]:
        """Get a bill by name (case-insensitive)"""
        response = (
            self.client.table("bills")
            .select("*")
            .eq("telegram_id", telegram_id)
            .eq("is_active", True)
            .ilike("name", name)
            .execute()
        )
        return response.data[0] if response.data else None

    def update_bill_sync(self, bill_id: str, data: Dict) -> Dict:
        """Update a bill"""
        response = self.client.table("bills").update(data).eq("id", bill_id).execute()
        return response.data[0] if response.data else None

    # ============ BANK ACCOUNT METHODS ============

    def add_bank_account_sync(self, telegram_id: int, bank_name: str, balance: float = 0, purpose: str = None) -> Dict:
        """Add a new bank account"""
        account_data = {
            "telegram_id": telegram_id,
            "bank_name": bank_name,
            "current_balance": balance,
            "purpose": purpose,
            "created_at": datetime.utcnow().isoformat()
        }
        response = self.client.table("bank_accounts").insert(account_data).execute()
        return response.data[0] if response.data else account_data

    def get_bank_accounts_sync(self, telegram_id: int) -> List[Dict]:
        """Get all active bank accounts for a user"""
        response = (
            self.client.table("bank_accounts")
            .select("*")
            .eq("telegram_id", telegram_id)
            .eq("is_active", True)
            .order("created_at")
            .execute()
        )
        return response.data

    def update_bank_balance_sync(self, account_id: str, new_balance: float) -> Dict:
        """Update a bank account balance"""
        response = (
            self.client.table("bank_accounts")
            .update({"current_balance": new_balance})
            .eq("id", account_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_bank_account_by_name_sync(self, telegram_id: int, bank_name: str) -> Optional[Dict]:
        """Get a bank account by name (case-insensitive)"""
        response = (
            self.client.table("bank_accounts")
            .select("*")
            .eq("telegram_id", telegram_id)
            .ilike("bank_name", bank_name)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete_bank_account_sync(self, account_id: str) -> bool:
        """Soft delete a bank account"""
        response = self.client.table("bank_accounts").update({"is_active": False}).eq("id", account_id).execute()
        return len(response.data) > 0

    # ============ CREDIT CARD METHODS ============

    def add_credit_card_sync(self, telegram_id: int, card_name: str, credit_limit: float,
                             due_date: int = None, statement_date: int = None) -> Dict:
        """Add a new credit card"""
        card_data = {
            "telegram_id": telegram_id,
            "card_name": card_name,
            "credit_limit": credit_limit,
            "current_balance": 0,
            "due_date": due_date,
            "statement_date": statement_date,
            "created_at": datetime.utcnow().isoformat()
        }
        response = self.client.table("credit_cards").insert(card_data).execute()
        return response.data[0] if response.data else card_data

    def get_credit_cards_sync(self, telegram_id: int) -> List[Dict]:
        """Get all active credit cards for a user"""
        response = (
            self.client.table("credit_cards")
            .select("*")
            .eq("telegram_id", telegram_id)
            .eq("is_active", True)
            .order("created_at")
            .execute()
        )
        return response.data

    def update_credit_card_balance_sync(self, card_id: str, balance: float) -> Dict:
        """Update a credit card balance"""
        response = (
            self.client.table("credit_cards")
            .update({"current_balance": balance})
            .eq("id", card_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_credit_card_by_name_sync(self, telegram_id: int, card_name: str) -> Optional[Dict]:
        """Get a credit card by name (case-insensitive)"""
        response = (
            self.client.table("credit_cards")
            .select("*")
            .eq("telegram_id", telegram_id)
            .ilike("card_name", card_name)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete_credit_card_sync(self, card_id: str) -> bool:
        """Soft delete a credit card"""
        response = self.client.table("credit_cards").update({"is_active": False}).eq("id", card_id).execute()
        return len(response.data) > 0

    # ============ SAVINGS/PAYOFF GOAL METHODS ============

    def add_goal_sync(self, telegram_id: int, name: str, goal_type: str, target_amount: float,
                      monthly_contribution: float = 0, priority: int = 1, target_date: str = None) -> Dict:
        """Add a new savings/payoff goal"""
        goal_data = {
            "telegram_id": telegram_id,
            "name": name,
            "goal_type": goal_type,
            "target_amount": target_amount,
            "current_amount": 0,
            "monthly_contribution": monthly_contribution,
            "priority": priority,
            "target_date": target_date,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        response = self.client.table("savings_goals").insert(goal_data).execute()
        return response.data[0] if response.data else goal_data

    def get_goals_sync(self, telegram_id: int, active_only: bool = True) -> List[Dict]:
        """Get all goals for a user"""
        query = (
            self.client.table("savings_goals")
            .select("*")
            .eq("telegram_id", telegram_id)
        )
        if active_only:
            query = query.eq("is_active", True)
        response = query.order("priority").execute()
        return response.data

    def get_goal_by_name_sync(self, telegram_id: int, name: str) -> Optional[Dict]:
        """Get a goal by name (case-insensitive)"""
        response = (
            self.client.table("savings_goals")
            .select("*")
            .eq("telegram_id", telegram_id)
            .ilike("name", name)
            .execute()
        )
        return response.data[0] if response.data else None

    def update_goal_sync(self, goal_id: str, data: Dict) -> Dict:
        """Update a goal"""
        response = self.client.table("savings_goals").update(data).eq("id", goal_id).execute()
        return response.data[0] if response.data else None

    def add_goal_payment_sync(self, goal_id: str, amount: float) -> Dict:
        """Add a payment to a goal (increases current_amount)"""
        goal = self.client.table("savings_goals").select("current_amount").eq("id", goal_id).execute()
        if goal.data:
            current = goal.data[0].get("current_amount", 0)
            new_amount = current + amount
            return self.update_goal_sync(goal_id, {"current_amount": new_amount})
        return None

    def delete_goal_sync(self, goal_id: str) -> bool:
        """Delete a goal (or mark as inactive)"""
        response = self.client.table("savings_goals").update({"is_active": False}).eq("id", goal_id).execute()
        return len(response.data) > 0

    # ============ PAY PERIOD METHODS ============

    def get_current_pay_period_sync(self, telegram_id: int) -> Optional[Dict]:
        """Get the current pay period for a user"""
        response = (
            self.client.table("pay_periods")
            .select("*")
            .eq("telegram_id", telegram_id)
            .eq("is_current", True)
            .execute()
        )
        return response.data[0] if response.data else None

    def create_pay_period_sync(self, telegram_id: int, start_date: str, end_date: str,
                               expected_income: float = None, actual_income: float = None,
                               rollover: float = 0) -> Dict:
        """Create a new pay period and mark it as current"""
        # First, mark any existing current period as not current
        self.client.table("pay_periods").update({"is_current": False}).eq("telegram_id", telegram_id).eq("is_current", True).execute()

        period_data = {
            "telegram_id": telegram_id,
            "period_start": start_date,
            "period_end": end_date,
            "expected_income": expected_income,
            "actual_income": actual_income,
            "rollover_amount": rollover,
            "is_current": True,
            "created_at": datetime.utcnow().isoformat()
        }
        response = self.client.table("pay_periods").insert(period_data).execute()
        return response.data[0] if response.data else period_data

    def close_pay_period_sync(self, period_id: str, rollover: float = 0) -> Dict:
        """Close a pay period and set rollover amount"""
        response = (
            self.client.table("pay_periods")
            .update({"is_current": False, "rollover_amount": rollover})
            .eq("id", period_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_pay_periods_sync(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Get recent pay periods for a user"""
        response = (
            self.client.table("pay_periods")
            .select("*")
            .eq("telegram_id", telegram_id)
            .order("period_start", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data

    # ============ TRANSACTION METHODS ============

    def add_transaction_sync(self, telegram_id: int, account_type: str, account_id: str,
                             transaction_type: str, amount: float, description: str = None) -> Dict:
        """Add a transaction record"""
        txn_data = {
            "telegram_id": telegram_id,
            "account_type": account_type,
            "account_id": account_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "description": description,
            "created_at": datetime.utcnow().isoformat()
        }
        response = self.client.table("transactions").insert(txn_data).execute()
        return response.data[0] if response.data else txn_data

    def get_transactions_sync(self, telegram_id: int, since: datetime = None, limit: int = 50) -> List[Dict]:
        """Get transactions for a user"""
        query = (
            self.client.table("transactions")
            .select("*")
            .eq("telegram_id", telegram_id)
        )
        if since:
            query = query.gte("created_at", since.isoformat())
        response = query.order("created_at", desc=True).limit(limit).execute()

        for txn in response.data:
            if isinstance(txn.get("created_at"), str):
                txn["created_at"] = date_parser.parse(txn["created_at"])

        return response.data

    def get_account_transactions_sync(self, account_type: str, account_id: str, limit: int = 20) -> List[Dict]:
        """Get transactions for a specific account"""
        response = (
            self.client.table("transactions")
            .select("*")
            .eq("account_type", account_type)
            .eq("account_id", account_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        for txn in response.data:
            if isinstance(txn.get("created_at"), str):
                txn["created_at"] = date_parser.parse(txn["created_at"])

        return response.data
