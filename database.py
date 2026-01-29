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
        """Get all bills for a user"""
        response = (
            self.client.table("bills")
            .select("*")
            .eq("telegram_id", telegram_id)
            .order("due_date")
            .execute()
        )
        return response.data

    def delete_bill_sync(self, bill_id: str) -> bool:
        """Delete a bill"""
        response = self.client.table("bills").delete().eq("id", bill_id).execute()
        return len(response.data) > 0

    def update_bill_sync(self, bill_id: str, data: Dict) -> Dict:
        """Update a bill"""
        response = self.client.table("bills").update(data).eq("id", bill_id).execute()
        return response.data[0] if response.data else None
