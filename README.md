# Budget Planner - FastAPI Application

A comprehensive personal budget planning application built with FastAPI, featuring beautiful charts, secure authentication, detailed expense tracking, and a **Variable Budget Tracker** for managing changing expenses throughout the month.

## Features

- **Secure Authentication**: Login/logout functionality with JWT tokens (365-day refresh tokens)
- **Interactive Dashboard**: 5 different chart types (Bar, Line, Pie, Area, Comparison)
- **Budget Entry**: Easy-to-use form for entering monthly income and expenses
- **Variable Budget Tracker**: Track and manage expenses that change throughout the month
- **Income Tracking**: Fixed income (Salary) and Variable income (Freelancing)
- **Expense Categories**: Mobile, WiFi, EMIs, Food, Rent, Credit Cards, Shopping, Travel, Other
- **Bucket List**: Track your wish list items and financial goals
- **Data Export**: Professional CSV/Excel export with filtering options
- **Responsive Design**: Works perfectly on desktop and mobile devices
- **Real-time Calculations**: Automatic calculation of totals and savings
- **INR Currency**: Indian Rupee (₹) currency support throughout the application

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite (local) / PostgreSQL (production)
- **Authentication**: JWT with bcrypt password hashing
- **Frontend**: Bootstrap 5, Chart.js for visualizations
- **Export**: Pandas and OpenPyXL for data export

## Deployment Instructions

### Deploy to Render

1. **Create a new Web Service** on Render
2. **Connect your GitHub repository** containing this code
3. **Configure the service**:
   - **Environment**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `python main.py`

4. **Set Environment Variables**:
   ```
   SECRET_KEY=your-super-secret-key-for-jwt-tokens
   REFRESH_SECRET_KEY=your-super-secret-refresh-key
   DATABASE_URL=postgresql://user:password@host:port/database
   PORT=10000
   ```

5. **Create a PostgreSQL Database** (add-on in Render):
   - Go to your dashboard and create a new PostgreSQL database
   - Copy the DATABASE_URL to your web service environment variables

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd budgetplanner
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

4. **Access the application**: Open http://localhost:8000

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key | `your-secret-key-here-change-in-production` |
| `REFRESH_SECRET_KEY` | JWT refresh secret key | `your-refresh-secret-key-here-change-in-production` |
| `DATABASE_URL` | Database connection URL | `sqlite:///./budget.db` |
| `PORT` | Application port | `8000` |
| `HOST` | Application host | `0.0.0.0` |

## Database

- **Development**: Uses SQLite for easy local development
- **Production**: Automatically supports PostgreSQL when DATABASE_URL is provided
- **Migration**: The application automatically creates tables on startup

## API Endpoints

- `/` - Dashboard with charts and analytics
- `/login` - Authentication
- `/budget` - Budget entry and management
- `/variable-budget` - Variable expense tracking
- `/bucket-list` - Bucket list management
- `/monthly-analysis` - Monthly expense analysis
- `/yearly-charts` - Yearly financial overview
- `/export/budget` - Data export interface
- `/api/*` - JSON API endpoints for charts and data

## Security Features

- **Password Hashing**: bcrypt for secure password storage
- **JWT Authentication**: Secure token-based authentication
- **Refresh Tokens**: 365-day refresh tokens for seamless experience
- **Input Validation**: Comprehensive input validation and sanitization
- **CSRF Protection**: Built-in CSRF protection for forms

## License

This project is open source and available under the MIT License.
2. **veerababu** / veera7474
3. **babu** / babu7474

## Installation & Setup

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python main.py
   ```

3. **Access the Application**:
   Open your browser and go to: `http://localhost:8000`

## File Structure

```
Budgetplanner/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── budget.db              # SQLite database (created automatically)
├── templates/             # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── budget.html
│   ├── budget_edit.html
│   ├── variable_budget.html  # 🆕 Variable budget tracker
│   ├── bucket_list.html
│   ├── bucket_add.html
│   ├── bucket_list_edit.html
│   ├── yearly_charts.html
│   └── monthly_analysis.html
└── static/               # Static files
    ├── css/
    │   ├── style.css
    │   └── login.css
    └── js/
        └── main.js
```

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT with PassLib for password hashing
- **UI Framework**: Bootstrap 5
- **Charts**: Chart.js
- **Icons**: Font Awesome

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Authentication
- `GET /logout` - Logout

### Budget Management
- `GET /` - Dashboard (requires authentication)
- `GET /budget` - Budget entry page
- `POST /budget` - Save budget entry
- `GET /budget/edit/{entry_id}` - Edit budget entry
- `POST /budget/update/{entry_id}` - Update budget entry
- `POST /budget/delete/{entry_id}` - Delete budget entry

### 🆕 Variable Budget
- `GET /variable-budget` - Variable budget tracker page
- `POST /variable-budget` - Add variable expense
- `POST /variable-budget/update/{entry_id}` - Update variable expense
- `POST /variable-budget/delete/{entry_id}` - Delete variable expense
- `POST /variable-budget/finalize` - Finalize monthly variable expenses

### Bucket List
- `GET /bucket-list` - Bucket list page
- `POST /bucket-list` - Add bucket list item
- `GET /bucket-list/edit/{item_id}` - Edit bucket list item
- `POST /bucket-list/update/{item_id}` - Update bucket list item
- `POST /bucket-list/complete/{item_id}` - Mark item as completed
- `POST /bucket-list/delete/{item_id}` - Delete bucket list item

### Charts & Analysis
- `GET /yearly-charts` - Yearly charts page
- `GET /monthly-analysis` - Monthly analysis page
- `GET /api/chart-data` - Chart data API

## Database Schema

### Users Table
- id (Primary Key)
- username (Unique)
- hashed_password

### Budget Entries Table
- id (Primary Key)
- user_id (Foreign Key)
- month, year
- Income fields: salary, freelancing_one, freelancing_two
- Expense fields: mobile_recharge, wifi, emi_one, emi_two, emi_three, emi_four, food, rent, creditcard_one, creditcard_two, shopping, travel, other_expenses
- created_at (Timestamp)

### 🆕 Variable Budget Entries Table
- id (Primary Key)
- user_id (Foreign Key)
- month, year
- category (food, travel, shopping, other)
- description
- amount
- date_added
- is_finalized (0=draft, 1=finalized)
- created_at, updated_at (Timestamps)

### Bucket List Table
- id (Primary Key)
- user_id (Foreign Key)
- name, category, price, description
- priority (High, Medium, Low)
- target_date
- is_completed (0=pending, 1=completed)
- created_at, completed_at (Timestamps)

## Security Features

- Password hashing with bcrypt
- JWT token authentication
- HTTP-only cookies
- Session management
- User isolation (users can only see their own data)

## Charts & Visualizations

1. **Income vs Expenses Bar Chart**: Monthly comparison
2. **Expense Breakdown Pie Chart**: Category-wise expense distribution
3. **Income Trend Line Chart**: Track income sources over time
4. **Savings Trend Area Chart**: Visualize savings pattern
5. **Monthly Comparison Chart**: Comprehensive monthly overview

## Customization

The application is highly customizable:

- Modify expense categories in `main.py`
- Update styling in `static/css/style.css`
- Add new chart types in `templates/dashboard.html`
- Extend database schema in `main.py`

## Production Deployment

For production deployment:

1. Change the `SECRET_KEY` in `main.py`
2. Set `secure=True` for cookies (requires HTTPS)
3. Use a production database (PostgreSQL/MySQL)
4. Configure proper environment variables
5. Use a production WSGI server like Gunicorn

## License

This project is open-source and available under the MIT License.
