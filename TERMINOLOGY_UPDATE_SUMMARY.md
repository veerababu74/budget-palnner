# Budget Planner - Terminology Clarification Update

## Summary of Changes Made

### 🎯 **Problem Addressed**
The user clarified that only **ETF, Fixed Deposits, and SIP** should be considered as actual investments/savings. Any remaining budget balance (income - expenses - investments) should NOT be labeled as "savings" but rather as "budget balance" or "remaining balance".

### 📊 **Backend API Changes**

#### 1. Updated Chart Data API (`/api/chart-data`)
- **Added proper savings structure**:
  ```json
  "savings": {
      "sip": [],
      "fixed_deposit_one": [],
      "fixed_deposit_two": [],
      "etf": [],
      "total": []
  }
  ```

#### 2. Updated Yearly Charts API (`/api/yearly-chart-data/{year}`)
- **Changed terminology**:
  - `"savings"` → `"investments"` (for actual SIP, FD, ETF)
  - `"savings"` → `"budget_balance"` (for income - expenses - investments)

- **New data structure**:
  ```json
  "monthly_totals": {
      "income": [],
      "expenses": [],
      "investments": [],
      "budget_balance": []
  }
  ```

#### 3. Updated Monthly Analysis API (`/api/monthly-analysis-data/{year}/{month}`)
- **Changed calculations**:
  - `current_savings` → `current_investments` (SIP + FD + ETF only)
  - `current_savings` → `current_budget_balance` (income - expenses - investments)
  - `savings_rate` → `investment_rate`

### 🎨 **Frontend Template Changes**

#### 1. Dashboard (`dashboard.html`)
- **Stats Card**: "Net Savings" → displays actual investments (SIP + FD + ETF)
- **Chart**: "Savings Trend" → "Budget Balance Trend"
- **Chart Function**: `savingsTrendChart` → `budgetBalanceChart`
- **Calculation**: Now shows budget balance = income - expenses - investments

#### 2. Yearly Charts (`yearly_charts.html`)
- **Summary Card**: "Total Savings" → "Budget Balance"
- **Chart Label**: "Savings" → "Budget Balance"
- **Chart Data**: Uses `budget_balance` instead of incorrectly calculated "savings"

#### 3. Monthly Analysis (`monthly_analysis.html`)
- **YTD Card**: "Monthly savings" → "Monthly investments"
- **Analytics**: "savings_rate" → "investment_rate"
- **Comparisons**: References to investments instead of savings

#### 4. Savings/Investments Dashboard (`savings_dashboard.html`)
- **Page Title**: "Savings Dashboard" → "Investments Dashboard"
- **Navigation**: "Savings Dashboard" → "Investments Dashboard"
- **Summary Cards**: Clarified terminology throughout

#### 5. Navigation (`base.html`)
- **Menu Item**: "Savings Dashboard" → "Investments Dashboard"

### 🔧 **Key Terminology Changes**

| **Old Term** | **New Term** | **What It Represents** |
|-------------|-------------|----------------------|
| "Savings" (calculated) | "Budget Balance" | Income - Expenses - Investments |
| "Savings" (input fields) | "Investments" | SIP + Fixed Deposits + ETF |
| "Savings Rate" | "Investment Rate" | Investments / Income * 100 |
| "Savings Trend" | "Budget Balance Trend" | Remaining money after expenses and investments |

### 💰 **What Each Term Now Means**

#### **Investments** (Actual Savings)
- **SIP (Systematic Investment Plan)**: Mutual fund investments
- **Fixed Deposit 1 & 2**: Bank fixed deposits
- **ETF**: Exchange Traded Fund investments

#### **Budget Balance** (Remaining Money)
- **Formula**: `Income - Expenses - Investments`
- **Meaning**: Money left over after paying expenses and making investments
- **Use**: Can be used for emergency fund, additional spending, or future investments

### 🎯 **Benefits of This Clarification**

1. **Accurate Financial Tracking**: Users now see true investment amounts vs remaining budget
2. **Better Decision Making**: Clear distinction between invested money and available money
3. **Proper Terminology**: Aligns with actual financial planning terms
4. **Separate Analytics**: Dedicated dashboard for tracking investment performance

### 📈 **Investment Dashboard Features**

1. **Separate Charts for Each Investment Type**:
   - Fixed Deposits (combines both FD accounts)
   - SIP Investments
   - ETF Investments
   - Total Investment Overview

2. **Advanced Analytics**:
   - Investment allocation pie chart
   - Monthly growth rates
   - Year-over-year comparisons

3. **Summary Cards**:
   - Real-time investment amounts
   - Growth percentages
   - Performance indicators

### 🔄 **Data Flow Example**

```
Monthly Budget Entry:
├── Income: ₹50,000
├── Expenses: ₹30,000
├── Investments:
│   ├── SIP: ₹5,000
│   ├── Fixed Deposit: ₹3,000
│   └── ETF: ₹2,000
│   └── Total: ₹10,000
└── Budget Balance: ₹10,000 (50k - 30k - 10k)
```

### 🎨 **Visual Indicators**

- **Green**: Positive budget balance (money left over)
- **Red**: Negative budget balance (overspending)
- **Blue**: Investment tracking (growth-focused)
- **Gold**: Mixed performance indicators

### 📱 **Responsive Design**

All terminology changes maintain the responsive design improvements:
- Works on all screen sizes (mobile to 4K)
- Touch-friendly interfaces
- Proper chart scaling
- Consistent visual hierarchy

This update ensures users have a clear understanding of their actual investments versus their available budget balance, leading to better financial planning and decision-making.
