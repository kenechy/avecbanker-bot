# AvecBanker Bot - Command Guide

Personal budget tracking bot for Telegram with multi-bank accounts, credit cards, goals, and pay period tracking.

---

## Quick Start

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and quick start guide |
| `/setup` | Configure income, bills, and budget split |
| `/help` | Show all available commands |
| `/dashboard` | Full financial overview |

---

## Expense Tracking

### Logging Expenses

Type naturally: `description amount category`

Categories:
- `needs` - Food, transport, essentials
- `wants` - Entertainment, shopping
- `savings` - Money set aside

Examples:
- `lunch 150 needs`
- `grab 85 needs`
- `coffee 180 wants`
- `netflix 550 wants`
- `emergency fund 1000 savings`

### Viewing Expenses

| Command | Description |
|---------|-------------|
| `/status` | Current month budget status with progress bars |
| `/history` | Last 10 expenses |
| `/summary` | Monthly breakdown by category |

---

## Bank Accounts

| Command | Description |
|---------|-------------|
| `/banks` | View all bank accounts with balances |
| `/addbank` | Add a new bank account |
| `/deposit` | Start deposit flow |
| `/withdraw` | Start withdrawal flow |
| `/transfer` | Transfer between accounts |

### Adding a Bank Account

After `/addbank`, enter: `BankName Balance Purpose`

Purpose options: savings, spending, allowance, emergency

Examples:
- `UnionBank 3300 savings`
- `BPI 10600 spending`
- `Maya 0 allowance`
- `GCash 0 allowance`

### Quick Inline Commands

- `deposit 5000 BPI` - Deposit P5,000 to BPI
- `withdraw 1000 UnionBank` - Withdraw P1,000 from UnionBank

### Transfers

After `/transfer`, enter: `FromBank ToBank Amount`

Example: `BPI UnionBank 5000`

---

## Credit Cards

| Command | Description |
|---------|-------------|
| `/cc` | View all credit cards with utilization |
| `/addcc` | Add a new credit card |
| `/ccpay` | Log a credit card payment |

### Adding a Credit Card

After `/addcc`, enter: `CardName Limit DueDate`

Examples:
- `BDO 50000 15`
- `Metrobank 100000 25`

### Logging Credit Card Spending

Quick inline command: `cc amount description`

Examples:
- `cc 500 shoes`
- `cc 1200 groceries`
- `cc 3500 gadget`

### Paying Credit Card

After `/ccpay`, enter: `CardName Amount`

Example: `BDO 5000`

---

## Goals & Payoff Tracking

| Command | Description |
|---------|-------------|
| `/goals` | View all active goals with progress |
| `/payoff` | View payoff goals only |
| `/addgoal` | Add a new goal |
| `/rebalance` | Recalculate goal contributions |
| `/simulate` | "What if" simulation for new goal |

### Adding a Goal

After `/addgoal`, enter: `Name Type TargetAmount MonthlyPayment TargetDate`

Goal types:
- `payoff` - Debt payoff (loans, etc.)
- `savings` - Emergency fund, vacation fund
- `purchase` - iPhone, laptop, etc.

Examples:
- `motorcycle payoff 208000 6500 2024-09-01`
- `iphone purchase 70000 7200 2024-12-01`
- `emergency savings 100000 5000`

### Making Goal Payments

Quick inline command: `paid goalname amount`

Examples:
- `paid motorcycle 6500` - Pay P6,500 to motorcycle
- `paid motorcycle` - Pay default monthly amount
- `paid emergency 2000` - Add P2,000 to emergency fund

### Simulating a New Goal

After `/simulate`, enter: `Name Amount TargetDate`

Example: `iphone 70000 2024-12-01`

Shows impact on existing goals without committing.

---

## Pay Periods (Bi-weekly)

| Command | Description |
|---------|-------------|
| `/payday` | Log payday and start new 14-day period |

### Starting a Pay Period

After `/payday`, enter:

First time: `Income StartDate`
- Example: `33040 2024-01-15`

Continuing: `Income`
- Example: `33040`

The bot automatically calculates daily spending limit and days remaining.

---

## Dashboard & Reports

| Command | Description |
|---------|-------------|
| `/dashboard` | Full financial overview |
| `/bills` | Upcoming bills with due dates |
| `/status` | Current budget status |
| `/summary` | Monthly expense breakdown |

### Dashboard Shows:
- All bank account balances
- Credit card utilization
- Current pay period status
- Payoff goal progress
- Upcoming bills with urgency indicators

### Bill Indicators:
- Red - Due today/tomorrow/3 days
- Yellow - Due within 7 days
- Green - Due later

---

## Budget Setup

After `/setup`, choose from the menu:

### Set Income
Enter monthly income: `83000`

Or for hourly USD: `$7/hr 176hrs`

### Set Fixed Bills
Enter each bill on a new line:
- `motorcycle 6500 7`
- `insurance 2500 30`
- `power 2000 28`
- `internet 1500 15`

### Set Budget Split
Enter 4 percentages that total 100: `needs wants savings extra`

Example: `23 7 18 52`
- 23% Needs
- 7% Wants
- 18% Savings
- 52% Extra (goals/payoff)

---

## Quick Reference

| Action | Command |
|--------|---------|
| Log expense | `lunch 150 needs` |
| Credit card spend | `cc 500 shoes` |
| Deposit to bank | `deposit 5000 BPI` |
| Withdraw from bank | `withdraw 1000 Maya` |
| Pay toward goal | `paid motorcycle 6500` |
| See everything | `/dashboard` |
| Check budget | `/status` |
| Check bills | `/bills` |
| Check banks | `/banks` |
| Check cards | `/cc` |
| Check goals | `/goals` |
