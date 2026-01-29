"""
Goal Calculator Module for AvecBanker Bot
Handles multi-goal budget calculations with priority-based allocation
"""

from datetime import datetime, date
from typing import List, Dict, Optional
from dateutil.relativedelta import relativedelta


class GoalCalculator:
    """Calculate goal contributions based on available budget and priorities"""

    def __init__(self, monthly_income: float, total_bills: float, extra_pct: float = 25):
        """
        Initialize calculator with budget parameters

        Args:
            monthly_income: Total monthly income
            total_bills: Sum of fixed monthly bills
            extra_pct: Percentage of available budget allocated to extra/goals
        """
        self.monthly_income = monthly_income
        self.total_bills = total_bills
        self.extra_pct = extra_pct

        # Calculate available extra pool
        available = monthly_income - total_bills
        self.extra_pool = available * (extra_pct / 100)

    def calculate_contributions(self, goals: List[Dict]) -> Dict:
        """
        Calculate monthly contributions for each goal based on priority

        Args:
            goals: List of goal dicts with keys:
                - name, goal_type, target_amount, current_amount,
                - monthly_contribution, priority, target_date

        Returns:
            Dict with:
                - extra_pool: Available monthly budget for goals
                - allocations: List of {name, monthly, months_to_goal, target_date}
                - unallocated: Remaining budget after all goals
                - warning: Warning message if budget is insufficient
        """
        if not goals:
            return {
                "extra_pool": self.extra_pool,
                "allocations": [],
                "unallocated": self.extra_pool,
                "warning": None
            }

        # Sort goals by priority (lower number = higher priority)
        sorted_goals = sorted(goals, key=lambda g: g.get("priority", 99))

        allocations = []
        remaining_pool = self.extra_pool
        warning = None

        for goal in sorted_goals:
            if not goal.get("is_active", True):
                continue

            name = goal.get("name", "Unknown")
            target = goal.get("target_amount", 0)
            current = goal.get("current_amount", 0)
            remaining_amount = max(target - current, 0)
            target_date = goal.get("target_date")
            priority = goal.get("priority", 99)

            if remaining_amount <= 0:
                # Goal already complete
                allocations.append({
                    "name": name,
                    "priority": priority,
                    "monthly": 0,
                    "months_to_goal": 0,
                    "target_date": target_date,
                    "remaining": 0,
                    "complete": True
                })
                continue

            # Calculate required monthly contribution to meet target date
            required_monthly = 0
            months_available = None

            if target_date:
                try:
                    if isinstance(target_date, str):
                        target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
                    else:
                        target_dt = target_date

                    today = date.today()
                    delta = relativedelta(target_dt, today)
                    months_available = max(delta.years * 12 + delta.months, 1)
                    required_monthly = remaining_amount / months_available
                except (ValueError, TypeError):
                    pass

            # Use existing monthly contribution or calculate based on target
            suggested_monthly = goal.get("monthly_contribution", 0)
            if suggested_monthly <= 0 and required_monthly > 0:
                suggested_monthly = required_monthly

            # Allocate from remaining pool
            if suggested_monthly > 0:
                allocated = min(suggested_monthly, remaining_pool)
            else:
                # No specific monthly set - allocate proportionally
                allocated = min(remaining_pool * 0.5, remaining_amount)

            remaining_pool -= allocated

            # Calculate months to goal at this contribution rate
            if allocated > 0:
                months_to_goal = remaining_amount / allocated
            else:
                months_to_goal = float('inf')

            allocations.append({
                "name": name,
                "priority": priority,
                "monthly": allocated,
                "months_to_goal": months_to_goal,
                "target_date": str(target_date) if target_date else None,
                "remaining": remaining_amount,
                "complete": False
            })

            # Check if allocation meets target date
            if months_available and months_to_goal > months_available:
                if not warning:
                    warning = f"Budget may not meet {name} target date. Consider reducing other goals or extending timeline."

        # Check for insufficient budget
        total_required = sum(a.get("monthly", 0) for a in allocations)
        if total_required > self.extra_pool and not warning:
            warning = f"Total goal contributions ({self._format_currency(total_required)}) exceed available extra budget ({self._format_currency(self.extra_pool)})"

        return {
            "extra_pool": self.extra_pool,
            "allocations": allocations,
            "unallocated": max(remaining_pool, 0),
            "warning": warning
        }

    def simulate_new_goal(self, existing_goals: List[Dict], new_goal: Dict) -> Dict:
        """
        Simulate adding a new goal and show impact on existing goals

        Args:
            existing_goals: Current list of goals
            new_goal: New goal to simulate adding

        Returns:
            Dict with before/after comparisons and impact analysis
        """
        # Calculate current state
        before = self.calculate_contributions(existing_goals)

        # Calculate with new goal
        all_goals = existing_goals + [new_goal]
        after = self.calculate_contributions(all_goals)

        # Analyze impact
        impact = []
        before_map = {a["name"]: a for a in before["allocations"]}
        after_map = {a["name"]: a for a in after["allocations"]}

        for name, before_alloc in before_map.items():
            if name in after_map:
                after_alloc = after_map[name]
                monthly_change = after_alloc["monthly"] - before_alloc["monthly"]
                timeline_change = after_alloc["months_to_goal"] - before_alloc["months_to_goal"]

                if abs(monthly_change) > 0.01 or abs(timeline_change) > 0.1:
                    impact.append({
                        "name": name,
                        "monthly_before": before_alloc["monthly"],
                        "monthly_after": after_alloc["monthly"],
                        "monthly_change": monthly_change,
                        "months_before": before_alloc["months_to_goal"],
                        "months_after": after_alloc["months_to_goal"],
                        "timeline_change": timeline_change
                    })

        return {
            "before": before,
            "after": after,
            "impact": impact,
            "new_goal_allocation": after_map.get(new_goal.get("name"))
        }

    def optimize_for_deadline(self, goal: Dict) -> Dict:
        """
        Calculate the minimum monthly contribution needed to meet a goal's deadline

        Args:
            goal: Goal dict with target_amount, current_amount, target_date

        Returns:
            Dict with required_monthly, is_feasible, shortfall
        """
        target = goal.get("target_amount", 0)
        current = goal.get("current_amount", 0)
        remaining = max(target - current, 0)
        target_date = goal.get("target_date")

        if not target_date:
            return {
                "required_monthly": 0,
                "is_feasible": True,
                "shortfall": 0,
                "message": "No target date set"
            }

        try:
            if isinstance(target_date, str):
                target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
            else:
                target_dt = target_date

            today = date.today()
            delta = relativedelta(target_dt, today)
            months_available = max(delta.years * 12 + delta.months, 1)
            required_monthly = remaining / months_available

            is_feasible = required_monthly <= self.extra_pool
            shortfall = max(required_monthly - self.extra_pool, 0)

            return {
                "required_monthly": required_monthly,
                "months_available": months_available,
                "is_feasible": is_feasible,
                "shortfall": shortfall,
                "message": f"Need {self._format_currency(required_monthly)}/month for {months_available} months"
            }
        except (ValueError, TypeError) as e:
            return {
                "required_monthly": 0,
                "is_feasible": False,
                "shortfall": 0,
                "message": f"Invalid target date: {e}"
            }

    def suggest_reallocation(self, goals: List[Dict], new_goal: Dict) -> List[Dict]:
        """
        Suggest how to reallocate existing goal contributions to fit a new goal

        Args:
            goals: Existing goals
            new_goal: New goal to add

        Returns:
            List of suggested adjustments
        """
        simulation = self.simulate_new_goal(goals, new_goal)
        suggestions = []

        new_allocation = simulation.get("new_goal_allocation", {})
        new_monthly = new_allocation.get("monthly", 0) if new_allocation else 0
        new_required = new_goal.get("monthly_contribution", 0) or self._calculate_required_monthly(new_goal)

        if new_monthly >= new_required:
            suggestions.append({
                "type": "success",
                "message": f"New goal fits within current budget allocation"
            })
            return suggestions

        shortfall = new_required - new_monthly

        # Look for lower priority goals that could be reduced
        sorted_goals = sorted(goals, key=lambda g: g.get("priority", 99), reverse=True)

        for goal in sorted_goals:
            if goal.get("priority", 99) <= new_goal.get("priority", 99):
                continue

            current_monthly = goal.get("monthly_contribution", 0)
            if current_monthly > 0:
                reducible = min(current_monthly * 0.3, shortfall)  # Max 30% reduction
                if reducible > 0:
                    suggestions.append({
                        "type": "reduce",
                        "goal_name": goal.get("name"),
                        "current_monthly": current_monthly,
                        "suggested_monthly": current_monthly - reducible,
                        "savings": reducible,
                        "impact_months": self._calculate_timeline_impact(goal, reducible)
                    })
                    shortfall -= reducible

        if shortfall > 0:
            suggestions.append({
                "type": "warning",
                "message": f"Still short {self._format_currency(shortfall)}/month. Consider extending timeline or increasing income allocation."
            })

        return suggestions

    def _calculate_required_monthly(self, goal: Dict) -> float:
        """Calculate required monthly contribution for a goal"""
        target = goal.get("target_amount", 0)
        current = goal.get("current_amount", 0)
        remaining = max(target - current, 0)
        target_date = goal.get("target_date")

        if not target_date or remaining <= 0:
            return 0

        try:
            if isinstance(target_date, str):
                target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
            else:
                target_dt = target_date

            today = date.today()
            delta = relativedelta(target_dt, today)
            months = max(delta.years * 12 + delta.months, 1)
            return remaining / months
        except (ValueError, TypeError):
            return 0

    def _calculate_timeline_impact(self, goal: Dict, reduction: float) -> float:
        """Calculate how many months a reduction adds to timeline"""
        remaining = goal.get("target_amount", 0) - goal.get("current_amount", 0)
        current_monthly = goal.get("monthly_contribution", 0)

        if current_monthly <= 0 or remaining <= 0:
            return 0

        current_months = remaining / current_monthly
        new_months = remaining / (current_monthly - reduction) if (current_monthly - reduction) > 0 else float('inf')

        return new_months - current_months

    def _format_currency(self, amount: float) -> str:
        """Format amount as Philippine Peso"""
        return f"₱{amount:,.2f}"
