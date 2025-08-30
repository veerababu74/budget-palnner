from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from contextlib import asynccontextmanager
import sqlite3
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup - Use environment variable for database URL or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./budget.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security - Use environment variables or defaults
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
REFRESH_SECRET_KEY = os.getenv(
    "REFRESH_SECRET_KEY", "your-refresh-secret-key-here-change-in-production"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = (
    365  # 1 year (effectively no expiration for user convenience)
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    is_revoked = Column(Integer, default=0)


class BudgetEntry(Base):
    __tablename__ = "budget_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    month = Column(String)
    year = Column(Integer)

    # Income
    salary = Column(Float, default=0.0)
    freelancing_one = Column(Float, default=0.0)
    freelancing_two = Column(Float, default=0.0)

    # Expenses
    mobile_recharge = Column(Float, default=0.0)
    wifi = Column(Float, default=0.0)
    emi_one = Column(Float, default=0.0)
    emi_two = Column(Float, default=0.0)
    emi_three = Column(Float, default=0.0)
    emi_four = Column(Float, default=0.0)
    food = Column(Float, default=0.0)
    rent = Column(Float, default=0.0)
    creditcard_one = Column(Float, default=0.0)
    creditcard_two = Column(Float, default=0.0)
    shopping = Column(Float, default=0.0)
    travel = Column(Float, default=0.0)
    other_expenses = Column(Float, default=0.0)

    # Savings/Investments
    sip = Column(Float, default=0.0)
    fixed_deposit_one = Column(Float, default=0.0)
    fixed_deposit_two = Column(Float, default=0.0)
    etf = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.now)


class VariableBudgetEntry(Base):
    __tablename__ = "variable_budget_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    month = Column(String)
    year = Column(Integer)
    category = Column(String)  # "food", "travel", "shopping", "other"
    description = Column(String, default="")
    amount = Column(Float, default=0.0)
    date_added = Column(DateTime, default=datetime.now)
    is_finalized = Column(
        Integer, default=0
    )  # 0 = draft, 1 = finalized to monthly budget
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)


class BucketList(Base):
    __tablename__ = "bucket_list"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    name = Column(String, nullable=False)
    category = Column(String, default="General")  # "Trips", "Gadgets", "General"
    price = Column(Float, nullable=False)
    description = Column(Text, default="")
    priority = Column(String, default="Medium")  # "High", "Medium", "Low"
    target_date = Column(String, default="")  # Target month/year to buy
    is_completed = Column(Integer, default=0)  # 0 = pending, 1 = completed
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, default=None)


# Create tables
Base.metadata.create_all(bind=engine)


# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = SessionLocal()
    init_users(db)
    db.close()
    yield
    # Shutdown (if needed)


# FastAPI app
app = FastAPI(
    title="Budget Planner",
    description="Personal Budget Planning Application",
    lifespan=lifespan,
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Password utilities
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, db: Session):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)

    # Store refresh token in database
    user_id = data.get("user_id")
    refresh_token = RefreshToken(
        user_id=user_id, token=encoded_jwt, expires_at=expire.replace(tzinfo=None)
    )
    db.add(refresh_token)
    db.commit()

    return encoded_jwt


def verify_refresh_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None

        # Check if token exists and is not revoked
        db_token = (
            db.query(RefreshToken)
            .filter(RefreshToken.token == token, RefreshToken.is_revoked == 0)
            .first()
        )

        if not db_token:
            return None

        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except JWTError:
        return None


def get_current_user(request: Request, db: Session = Depends(get_db)):
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    if access_token:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") == "access":
                username: str = payload.get("sub")
                if username:
                    user = db.query(User).filter(User.username == username).first()
                    return user
        except JWTError:
            pass

    # If access token is invalid/expired, try refresh token
    if refresh_token:
        user = verify_refresh_token(refresh_token, db)
        if user:
            # Generate new access token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            new_access_token = create_access_token(
                data={"sub": user.username, "user_id": user.id},
                expires_delta=access_token_expires,
            )
            # Note: We'll set the new cookie in the response later
            return user

    return None


# Initialize default users
def init_users(db: Session):
    users_data = [
        {"username": "veera", "password": "veera7474"},
        {"username": "veerababu", "password": "veera7474"},
        {"username": "babu", "password": "babu7474"},
    ]

    for user_data in users_data:
        existing_user = (
            db.query(User).filter(User.username == user_data["username"]).first()
        )
        if not existing_user:
            hashed_password = get_password_hash(user_data["password"])
            user = User(username=user_data["username"], hashed_password=hashed_password)
            db.add(user)

    db.commit()


# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get latest budget entry
    latest_entry = (
        db.query(BudgetEntry)
        .filter(BudgetEntry.user_id == current_user.id)
        .order_by(BudgetEntry.created_at.desc())
        .first()
    )

    # Get all entries for charts
    all_entries = (
        db.query(BudgetEntry).filter(BudgetEntry.user_id == current_user.id).all()
    )

    # Get bucket list stats
    total_bucket_items = (
        db.query(BucketList).filter(BucketList.user_id == current_user.id).count()
    )
    completed_bucket_items = (
        db.query(BucketList)
        .filter(BucketList.user_id == current_user.id, BucketList.is_completed == 1)
        .count()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "latest_entry": latest_entry,
            "all_entries": all_entries,
            "total_bucket_items": total_bucket_items,
            "completed_bucket_items": completed_bucket_items,
        },
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid username or password"}
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires,
    )

    # Create refresh token
    refresh_token = create_refresh_token(
        data={"user_id": user.id, "sub": user.username}, db=db
    )

    response = RedirectResponse("/", status_code=302)

    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        path="/",
        samesite="lax",
    )

    # Set refresh token cookie (longer expiration)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Days to seconds
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        path="/",
        samesite="lax",
    )

    return response


@app.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    # Revoke refresh token if exists
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        db_token = (
            db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        )
        if db_token:
            db_token.is_revoked = 1
            db.commit()

    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


@app.get("/budget", response_class=HTMLResponse)
async def budget_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get all budget entries for the user
    entries = (
        db.query(BudgetEntry)
        .filter(BudgetEntry.user_id == current_user.id)
        .order_by(BudgetEntry.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "budget.html", {"request": request, "user": current_user, "entries": entries}
    )


@app.post("/budget")
async def save_budget(
    request: Request,
    salary: float = Form(0.0),
    freelancing_one: float = Form(0.0),
    freelancing_two: float = Form(0.0),
    mobile_recharge: float = Form(0.0),
    wifi: float = Form(0.0),
    emi_one: float = Form(0.0),
    emi_two: float = Form(0.0),
    emi_three: float = Form(0.0),
    emi_four: float = Form(0.0),
    food: float = Form(0.0),
    rent: float = Form(0.0),
    creditcard_one: float = Form(0.0),
    creditcard_two: float = Form(0.0),
    shopping: float = Form(0.0),
    travel: float = Form(0.0),
    other_expenses: float = Form(0.0),
    sip: float = Form(0.0),
    fixed_deposit_one: float = Form(0.0),
    fixed_deposit_two: float = Form(0.0),
    etf: float = Form(0.0),
    confirm_overwrite: str = Form(""),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Use current month and year automatically
    now = datetime.now()
    current_month = now.strftime("%B")
    current_year = now.year

    # Check if entry exists for this month/year
    existing_entry = (
        db.query(BudgetEntry)
        .filter(
            BudgetEntry.user_id == current_user.id,
            BudgetEntry.month == current_month,
            BudgetEntry.year == current_year,
        )
        .first()
    )

    if existing_entry and confirm_overwrite != "yes":
        # Return to budget page with warning if entry exists and no confirmation
        entries = (
            db.query(BudgetEntry)
            .filter(BudgetEntry.user_id == current_user.id)
            .order_by(BudgetEntry.year.desc(), BudgetEntry.month.desc())
            .all()
        )
        return templates.TemplateResponse(
            "budget.html",
            {
                "request": request,
                "user": current_user,
                "entries": entries,
                "existing_entry": existing_entry,
                "show_warning": True,
                "form_data": {
                    "salary": salary,
                    "freelancing_one": freelancing_one,
                    "freelancing_two": freelancing_two,
                    "mobile_recharge": mobile_recharge,
                    "wifi": wifi,
                    "emi_one": emi_one,
                    "emi_two": emi_two,
                    "emi_three": emi_three,
                    "emi_four": emi_four,
                    "food": food,
                    "rent": rent,
                    "creditcard_one": creditcard_one,
                    "creditcard_two": creditcard_two,
                    "shopping": shopping,
                    "travel": travel,
                    "other_expenses": other_expenses,
                    "sip": sip,
                    "fixed_deposit_one": fixed_deposit_one,
                    "fixed_deposit_two": fixed_deposit_two,
                    "etf": etf,
                },
            },
        )

    if existing_entry:
        # Update existing entry only if confirmed
        existing_entry.salary = salary
        existing_entry.freelancing_one = freelancing_one
        existing_entry.freelancing_two = freelancing_two
        existing_entry.mobile_recharge = mobile_recharge
        existing_entry.wifi = wifi
        existing_entry.emi_one = emi_one
        existing_entry.emi_two = emi_two
        existing_entry.emi_three = emi_three
        existing_entry.emi_four = emi_four
        existing_entry.food = food
        existing_entry.rent = rent
        existing_entry.creditcard_one = creditcard_one
        existing_entry.creditcard_two = creditcard_two
        existing_entry.shopping = shopping
        existing_entry.travel = travel
        existing_entry.other_expenses = other_expenses
        existing_entry.sip = sip
        existing_entry.fixed_deposit_one = fixed_deposit_one
        existing_entry.fixed_deposit_two = fixed_deposit_two
        existing_entry.etf = etf
    else:
        # Create new entry
        budget_entry = BudgetEntry(
            user_id=current_user.id,
            month=current_month,
            year=current_year,
            salary=salary,
            freelancing_one=freelancing_one,
            freelancing_two=freelancing_two,
            mobile_recharge=mobile_recharge,
            wifi=wifi,
            emi_one=emi_one,
            emi_two=emi_two,
            emi_three=emi_three,
            emi_four=emi_four,
            food=food,
            rent=rent,
            creditcard_one=creditcard_one,
            creditcard_two=creditcard_two,
            shopping=shopping,
            travel=travel,
            other_expenses=other_expenses,
            sip=sip,
            fixed_deposit_one=fixed_deposit_one,
            fixed_deposit_two=fixed_deposit_two,
            etf=etf,
        )
        db.add(budget_entry)

    db.commit()
    return RedirectResponse("/budget", status_code=302)


@app.get("/budget/edit/{entry_id}")
async def edit_budget_page(
    entry_id: int, request: Request, db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get the specific entry
    entry = (
        db.query(BudgetEntry)
        .filter(BudgetEntry.id == entry_id, BudgetEntry.user_id == current_user.id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Budget entry not found")

    # Get all entries for the sidebar
    entries = (
        db.query(BudgetEntry)
        .filter(BudgetEntry.user_id == current_user.id)
        .order_by(BudgetEntry.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "budget_edit.html",
        {"request": request, "user": current_user, "entry": entry, "entries": entries},
    )


@app.post("/budget/update/{entry_id}")
async def update_budget(
    entry_id: int,
    request: Request,
    salary: float = Form(0.0),
    freelancing_one: float = Form(0.0),
    freelancing_two: float = Form(0.0),
    mobile_recharge: float = Form(0.0),
    wifi: float = Form(0.0),
    emi_one: float = Form(0.0),
    emi_two: float = Form(0.0),
    emi_three: float = Form(0.0),
    emi_four: float = Form(0.0),
    food: float = Form(0.0),
    rent: float = Form(0.0),
    creditcard_one: float = Form(0.0),
    creditcard_two: float = Form(0.0),
    shopping: float = Form(0.0),
    travel: float = Form(0.0),
    other_expenses: float = Form(0.0),
    sip: float = Form(0.0),
    fixed_deposit_one: float = Form(0.0),
    fixed_deposit_two: float = Form(0.0),
    etf: float = Form(0.0),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get the entry to update
    entry = (
        db.query(BudgetEntry)
        .filter(BudgetEntry.id == entry_id, BudgetEntry.user_id == current_user.id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Budget entry not found")

    # Update the entry
    entry.salary = salary
    entry.freelancing_one = freelancing_one
    entry.freelancing_two = freelancing_two
    entry.mobile_recharge = mobile_recharge
    entry.wifi = wifi
    entry.emi_one = emi_one
    entry.emi_two = emi_two
    entry.emi_three = emi_three
    entry.emi_four = emi_four
    entry.food = food
    entry.rent = rent
    entry.creditcard_one = creditcard_one
    entry.creditcard_two = creditcard_two
    entry.shopping = shopping
    entry.travel = travel
    entry.other_expenses = other_expenses
    entry.sip = sip
    entry.fixed_deposit_one = fixed_deposit_one
    entry.fixed_deposit_two = fixed_deposit_two
    entry.etf = etf

    db.commit()
    return RedirectResponse("/budget", status_code=302)


@app.post("/budget/delete/{entry_id}")
async def delete_budget(entry_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get the entry to delete
    entry = (
        db.query(BudgetEntry)
        .filter(BudgetEntry.id == entry_id, BudgetEntry.user_id == current_user.id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Budget entry not found")

    db.delete(entry)
    db.commit()
    return RedirectResponse("/budget", status_code=302)


@app.get("/api/chart-data")
async def get_chart_data(
    request: Request, timespan: str = "all", db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    entries_query = db.query(BudgetEntry).filter(BudgetEntry.user_id == current_user.id)

    # Filter by timespan
    if timespan != "all":
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        if timespan == "current_month":
            entries_query = entries_query.filter(
                BudgetEntry.year == current_year,
                BudgetEntry.month == current_date.strftime("%B"),
            )
        elif timespan == "quarter":
            # Current quarter
            quarter_start = ((current_month - 1) // 3) * 3 + 1
            quarter_months = []
            for i in range(3):
                month_num = quarter_start + i
                if month_num <= 12:
                    quarter_months.append(
                        datetime(current_year, month_num, 1).strftime("%B")
                    )
            entries_query = entries_query.filter(
                BudgetEntry.year == current_year, BudgetEntry.month.in_(quarter_months)
            )
        elif timespan == "half_year":
            # Current half year
            if current_month <= 6:
                half_months = [
                    datetime(current_year, i, 1).strftime("%B") for i in range(1, 7)
                ]
            else:
                half_months = [
                    datetime(current_year, i, 1).strftime("%B") for i in range(7, 13)
                ]
            entries_query = entries_query.filter(
                BudgetEntry.year == current_year, BudgetEntry.month.in_(half_months)
            )
        elif timespan == "current_year":
            entries_query = entries_query.filter(BudgetEntry.year == current_year)

    entries = entries_query.order_by(BudgetEntry.year, BudgetEntry.month).all()

    chart_data = {
        "months": [],
        "income": {
            "salary": [],
            "freelancing_one": [],
            "freelancing_two": [],
            "total": [],
        },
        "expenses": {
            "mobile_recharge": [],
            "wifi": [],
            "emi_one": [],
            "emi_two": [],
            "emi_three": [],
            "emi_four": [],
            "food": [],
            "rent": [],
            "creditcard_one": [],
            "creditcard_two": [],
            "shopping": [],
            "travel": [],
            "other_expenses": [],
            "total": [],
        },
        "savings": {
            "sip": [],
            "fixed_deposit_one": [],
            "fixed_deposit_two": [],
            "etf": [],
            "total": [],
        },
    }

    for entry in entries:
        month_year = f"{entry.month} {entry.year}"
        chart_data["months"].append(month_year)

        # Income data
        chart_data["income"]["salary"].append(entry.salary)
        chart_data["income"]["freelancing_one"].append(entry.freelancing_one)
        chart_data["income"]["freelancing_two"].append(entry.freelancing_two)
        total_income = entry.salary + entry.freelancing_one + entry.freelancing_two
        chart_data["income"]["total"].append(total_income)

        # Expense data
        chart_data["expenses"]["mobile_recharge"].append(entry.mobile_recharge)
        chart_data["expenses"]["wifi"].append(entry.wifi)
        chart_data["expenses"]["emi_one"].append(entry.emi_one)
        chart_data["expenses"]["emi_two"].append(entry.emi_two)
        chart_data["expenses"]["emi_three"].append(entry.emi_three)
        chart_data["expenses"]["emi_four"].append(entry.emi_four)
        chart_data["expenses"]["food"].append(entry.food)
        chart_data["expenses"]["rent"].append(entry.rent)
        chart_data["expenses"]["creditcard_one"].append(entry.creditcard_one)
        chart_data["expenses"]["creditcard_two"].append(entry.creditcard_two)
        chart_data["expenses"]["shopping"].append(entry.shopping)
        chart_data["expenses"]["travel"].append(entry.travel)
        chart_data["expenses"]["other_expenses"].append(entry.other_expenses)

        total_expenses = (
            entry.mobile_recharge
            + entry.wifi
            + entry.emi_one
            + entry.emi_two
            + entry.emi_three
            + entry.emi_four
            + entry.food
            + entry.rent
            + entry.creditcard_one
            + entry.creditcard_two
            + entry.shopping
            + entry.travel
            + entry.other_expenses
        )
        chart_data["expenses"]["total"].append(total_expenses)

        # Savings data
        chart_data["savings"]["sip"].append(entry.sip)
        chart_data["savings"]["fixed_deposit_one"].append(entry.fixed_deposit_one)
        chart_data["savings"]["fixed_deposit_two"].append(entry.fixed_deposit_two)
        chart_data["savings"]["etf"].append(entry.etf)

        total_savings = (
            entry.sip + entry.fixed_deposit_one + entry.fixed_deposit_two + entry.etf
        )
        chart_data["savings"]["total"].append(total_savings)

    return chart_data


@app.get("/api-test", response_class=HTMLResponse)
async def api_test_page(request: Request):
    return templates.TemplateResponse("api_test.html", {"request": request})


@app.get("/savings-dashboard", response_class=HTMLResponse)
async def savings_dashboard(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    # Get current month for display
    current_month = datetime.now().strftime("%B %Y")

    # Check if user has any budget entries
    entries_count = (
        db.query(BudgetEntry).filter(BudgetEntry.user_id == current_user.id).count()
    )

    # Check if user has any savings/investment data
    savings_entries = (
        db.query(BudgetEntry)
        .filter(
            BudgetEntry.user_id == current_user.id,
            (BudgetEntry.sip > 0)
            | (BudgetEntry.fixed_deposit_one > 0)
            | (BudgetEntry.fixed_deposit_two > 0)
            | (BudgetEntry.etf > 0),
        )
        .count()
    )

    return templates.TemplateResponse(
        "savings_dashboard.html",
        {
            "request": request,
            "user": current_user,
            "current_month": current_month,
            "entries_count": entries_count,
            "savings_entries": savings_entries,
        },
    )


# Variable Budget Routes
@app.get("/variable-budget", response_class=HTMLResponse)
async def variable_budget_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get current month and year
    now = datetime.now()
    current_month = now.strftime("%B")
    current_year = now.year

    # Get all variable budget entries for current month
    variable_entries = (
        db.query(VariableBudgetEntry)
        .filter(
            VariableBudgetEntry.user_id == current_user.id,
            VariableBudgetEntry.month == current_month,
            VariableBudgetEntry.year == current_year,
        )
        .order_by(VariableBudgetEntry.created_at.desc())
        .all()
    )

    # Group entries by category
    grouped_entries = {}
    for entry in variable_entries:
        if entry.category not in grouped_entries:
            grouped_entries[entry.category] = []
        grouped_entries[entry.category].append(entry)

    # Calculate totals by category
    category_totals = {}
    for category, entries in grouped_entries.items():
        category_totals[category] = sum(
            entry.amount for entry in entries if not entry.is_finalized
        )

    return templates.TemplateResponse(
        "variable_budget.html",
        {
            "request": request,
            "user": current_user,
            "grouped_entries": grouped_entries,
            "category_totals": category_totals,
            "current_month": current_month,
            "current_year": current_year,
        },
    )


@app.post("/variable-budget")
async def add_variable_budget(
    request: Request,
    category: str = Form(...),
    description: str = Form(...),
    amount: float = Form(...),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get current month and year
    now = datetime.now()
    current_month = now.strftime("%B")
    current_year = now.year

    # Create new variable budget entry
    variable_entry = VariableBudgetEntry(
        user_id=current_user.id,
        month=current_month,
        year=current_year,
        category=category,
        description=description,
        amount=amount,
    )

    db.add(variable_entry)
    db.commit()
    return RedirectResponse("/variable-budget", status_code=302)


@app.post("/variable-budget/update/{entry_id}")
async def update_variable_budget(
    entry_id: int,
    request: Request,
    description: str = Form(...),
    amount: float = Form(...),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get the entry to update
    entry = (
        db.query(VariableBudgetEntry)
        .filter(
            VariableBudgetEntry.id == entry_id,
            VariableBudgetEntry.user_id == current_user.id,
            VariableBudgetEntry.is_finalized == 0,
        )
        .first()
    )

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Variable budget entry not found or already finalized",
        )

    # Update the entry
    entry.description = description
    entry.amount = amount
    entry.updated_at = datetime.now()

    db.commit()
    return RedirectResponse("/variable-budget", status_code=302)


@app.post("/variable-budget/delete/{entry_id}")
async def delete_variable_budget(
    entry_id: int, request: Request, db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get the entry to delete
    entry = (
        db.query(VariableBudgetEntry)
        .filter(
            VariableBudgetEntry.id == entry_id,
            VariableBudgetEntry.user_id == current_user.id,
            VariableBudgetEntry.is_finalized == 0,
        )
        .first()
    )

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Variable budget entry not found or already finalized",
        )

    db.delete(entry)
    db.commit()
    return RedirectResponse("/variable-budget", status_code=302)


@app.post("/variable-budget/finalize")
async def finalize_variable_budget(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get current month and year
    now = datetime.now()
    current_month = now.strftime("%B")
    current_year = now.year

    # Get all non-finalized variable entries for current month
    variable_entries = (
        db.query(VariableBudgetEntry)
        .filter(
            VariableBudgetEntry.user_id == current_user.id,
            VariableBudgetEntry.month == current_month,
            VariableBudgetEntry.year == current_year,
            VariableBudgetEntry.is_finalized == 0,
        )
        .all()
    )

    if not variable_entries:
        return RedirectResponse("/variable-budget", status_code=302)

    # Calculate totals by category
    category_totals = {}
    for entry in variable_entries:
        if entry.category not in category_totals:
            category_totals[entry.category] = 0
        category_totals[entry.category] += entry.amount

    # Get or create budget entry for current month
    budget_entry = (
        db.query(BudgetEntry)
        .filter(
            BudgetEntry.user_id == current_user.id,
            BudgetEntry.month == current_month,
            BudgetEntry.year == current_year,
        )
        .first()
    )

    if not budget_entry:
        # Create new budget entry if it doesn't exist
        budget_entry = BudgetEntry(
            user_id=current_user.id,
            month=current_month,
            year=current_year,
        )
        db.add(budget_entry)

    # Update budget entry with variable amounts
    for category, total in category_totals.items():
        if category == "food":
            budget_entry.food += total
        elif category == "travel":
            budget_entry.travel += total
        elif category == "shopping":
            budget_entry.shopping += total
        elif category == "other":
            budget_entry.other_expenses += total

    # Mark all variable entries as finalized
    for entry in variable_entries:
        entry.is_finalized = 1

    db.commit()
    return RedirectResponse("/budget", status_code=302)


# Bucket List Routes
@app.get("/bucket-list", response_class=HTMLResponse)
async def bucket_list_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get all bucket list items for the user
    bucket_items = (
        db.query(BucketList)
        .filter(BucketList.user_id == current_user.id)
        .order_by(BucketList.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "bucket_list.html",
        {"request": request, "user": current_user, "bucket_items": bucket_items},
    )


@app.get("/bucket-list/add", response_class=HTMLResponse)
async def bucket_add_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    return templates.TemplateResponse(
        "bucket_add.html",
        {"request": request, "user": current_user},
    )


@app.post("/bucket-list")
async def add_bucket_item(
    request: Request,
    name: str = Form(...),
    category: str = Form("General"),
    price: float = Form(...),
    description: str = Form(""),
    priority: str = Form("Medium"),
    target_date: str = Form(""),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    bucket_item = BucketList(
        user_id=current_user.id,
        name=name,
        category=category,
        price=price,
        description=description,
        priority=priority,
        target_date=target_date,
    )
    db.add(bucket_item)
    db.commit()

    return RedirectResponse("/bucket-list", status_code=302)


@app.get("/bucket-list/edit/{item_id}")
async def edit_bucket_item_page(
    item_id: int, request: Request, db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get the specific item
    item = (
        db.query(BucketList)
        .filter(BucketList.id == item_id, BucketList.user_id == current_user.id)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Bucket list item not found")

    # Get all items for the sidebar
    bucket_items = (
        db.query(BucketList)
        .filter(BucketList.user_id == current_user.id)
        .order_by(BucketList.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "bucket_list_edit.html",
        {
            "request": request,
            "user": current_user,
            "item": item,
            "bucket_items": bucket_items,
        },
    )


@app.post("/bucket-list/update/{item_id}")
async def update_bucket_item(
    item_id: int,
    request: Request,
    name: str = Form(...),
    category: str = Form("General"),
    price: float = Form(...),
    description: str = Form(""),
    priority: str = Form("Medium"),
    target_date: str = Form(""),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get the item to update
    item = (
        db.query(BucketList)
        .filter(BucketList.id == item_id, BucketList.user_id == current_user.id)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Bucket list item not found")

    # Update the item
    item.name = name
    item.category = category
    item.price = price
    item.description = description
    item.priority = priority
    item.target_date = target_date

    db.commit()
    return RedirectResponse("/bucket-list", status_code=302)


@app.post("/bucket-list/complete/{item_id}")
async def complete_bucket_item(
    item_id: int, request: Request, db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get the item to complete
    item = (
        db.query(BucketList)
        .filter(BucketList.id == item_id, BucketList.user_id == current_user.id)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Bucket list item not found")

    item.is_completed = 1
    item.completed_at = datetime.now()
    db.commit()
    return RedirectResponse("/bucket-list", status_code=302)


@app.post("/bucket-list/delete/{item_id}")
async def delete_bucket_item(
    item_id: int, request: Request, db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get the item to delete
    item = (
        db.query(BucketList)
        .filter(BucketList.id == item_id, BucketList.user_id == current_user.id)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Bucket list item not found")

    db.delete(item)
    db.commit()
    return RedirectResponse("/bucket-list", status_code=302)


# Yearly Financial Charts Routes
@app.get("/yearly-charts", response_class=HTMLResponse)
async def yearly_charts(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get available years from user's budget entries
    years = (
        db.query(BudgetEntry.year)
        .filter(BudgetEntry.user_id == current_user.id)
        .distinct()
        .order_by(BudgetEntry.year.desc())
        .all()
    )
    available_years = [year[0] for year in years]

    # Default to current year if no data exists
    if not available_years:
        available_years = [datetime.now().year]

    return templates.TemplateResponse(
        "yearly_charts.html",
        {
            "request": request,
            "user": current_user,
            "available_years": available_years,
        },
    )


@app.get("/api/yearly-chart-data/{year}")
async def get_yearly_chart_data(
    year: int, request: Request, db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get all entries for the specified year
    entries = (
        db.query(BudgetEntry)
        .filter(BudgetEntry.user_id == current_user.id, BudgetEntry.year == year)
        .order_by(BudgetEntry.month)
        .all()
    )

    # Month order for proper sorting
    month_order = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    # Initialize data structure
    yearly_data = {
        "year": year,
        "months": [],
        "monthly_totals": {
            "income": [],
            "expenses": [],
            "investments": [],
            "budget_balance": [],
        },
        "income_breakdown": {
            "salary": [],
            "freelancing_one": [],
            "freelancing_two": [],
        },
        "expense_breakdown": {
            "mobile_recharge": [],
            "wifi": [],
            "emi_total": [],
            "food": [],
            "rent": [],
            "creditcard_total": [],
            "shopping": [],
            "travel": [],
            "other_expenses": [],
        },
        "investment_breakdown": {
            "sip": [],
            "fixed_deposit_one": [],
            "fixed_deposit_two": [],
            "etf": [],
        },
        "monthly_comparison": {
            "months": [],
            "income": [],
            "expenses": [],
            "investments": [],
            "budget_balance": [],
        },
    }

    # Create a dictionary for quick lookup
    entries_by_month = {entry.month: entry for entry in entries}

    # Process data for each month
    for month in month_order:
        entry = entries_by_month.get(month)

        if entry:
            yearly_data["months"].append(month)

            # Calculate totals
            total_income = entry.salary + entry.freelancing_one + entry.freelancing_two
            total_expenses = (
                entry.mobile_recharge
                + entry.wifi
                + entry.emi_one
                + entry.emi_two
                + entry.emi_three
                + entry.emi_four
                + entry.food
                + entry.rent
                + entry.creditcard_one
                + entry.creditcard_two
                + entry.shopping
                + entry.travel
                + entry.other_expenses
            )
            # Calculate actual investments/savings (only SIP, FD, ETF)
            total_investments = (
                entry.sip
                + entry.fixed_deposit_one
                + entry.fixed_deposit_two
                + entry.etf
            )
            # Calculate remaining budget balance (not savings)
            budget_balance = total_income - total_expenses - total_investments

            # Monthly totals
            yearly_data["monthly_totals"]["income"].append(total_income)
            yearly_data["monthly_totals"]["expenses"].append(total_expenses)
            yearly_data["monthly_totals"]["investments"].append(total_investments)
            yearly_data["monthly_totals"]["budget_balance"].append(budget_balance)

            # Income breakdown
            yearly_data["income_breakdown"]["salary"].append(entry.salary)
            yearly_data["income_breakdown"]["freelancing_one"].append(
                entry.freelancing_one
            )
            yearly_data["income_breakdown"]["freelancing_two"].append(
                entry.freelancing_two
            )

            # Expense breakdown
            yearly_data["expense_breakdown"]["mobile_recharge"].append(
                entry.mobile_recharge
            )
            yearly_data["expense_breakdown"]["wifi"].append(entry.wifi)
            yearly_data["expense_breakdown"]["emi_total"].append(
                entry.emi_one + entry.emi_two + entry.emi_three + entry.emi_four
            )
            yearly_data["expense_breakdown"]["food"].append(entry.food)
            yearly_data["expense_breakdown"]["rent"].append(entry.rent)
            yearly_data["expense_breakdown"]["creditcard_total"].append(
                entry.creditcard_one + entry.creditcard_two
            )
            yearly_data["expense_breakdown"]["shopping"].append(entry.shopping)
            yearly_data["expense_breakdown"]["travel"].append(entry.travel)
            yearly_data["expense_breakdown"]["other_expenses"].append(
                entry.other_expenses
            )

            # Investment breakdown
            yearly_data["investment_breakdown"]["sip"].append(entry.sip)
            yearly_data["investment_breakdown"]["fixed_deposit_one"].append(
                entry.fixed_deposit_one
            )
            yearly_data["investment_breakdown"]["fixed_deposit_two"].append(
                entry.fixed_deposit_two
            )
            yearly_data["investment_breakdown"]["etf"].append(entry.etf)

            # Monthly comparison data
            yearly_data["monthly_comparison"]["months"].append(
                month[:3]
            )  # Short month name
            yearly_data["monthly_comparison"]["income"].append(total_income)
            yearly_data["monthly_comparison"]["expenses"].append(total_expenses)
            yearly_data["monthly_comparison"]["investments"].append(total_investments)
            yearly_data["monthly_comparison"]["budget_balance"].append(budget_balance)

    # Calculate year summary
    yearly_data["summary"] = {
        "total_income": sum(yearly_data["monthly_totals"]["income"]),
        "total_expenses": sum(yearly_data["monthly_totals"]["expenses"]),
        "total_investments": sum(yearly_data["monthly_totals"]["investments"]),
        "total_budget_balance": sum(yearly_data["monthly_totals"]["budget_balance"]),
        "average_monthly_income": sum(yearly_data["monthly_totals"]["income"])
        / max(len(yearly_data["monthly_totals"]["income"]), 1),
        "average_monthly_expenses": sum(yearly_data["monthly_totals"]["expenses"])
        / max(len(yearly_data["monthly_totals"]["expenses"]), 1),
        "average_monthly_investments": sum(yearly_data["monthly_totals"]["investments"])
        / max(len(yearly_data["monthly_totals"]["investments"]), 1),
        "average_monthly_budget_balance": sum(
            yearly_data["monthly_totals"]["budget_balance"]
        )
        / max(len(yearly_data["monthly_totals"]["budget_balance"]), 1),
        "months_with_data": len(yearly_data["months"]),
    }

    return yearly_data


# Monthly Analysis Routes
@app.get("/monthly-analysis", response_class=HTMLResponse)
async def monthly_analysis(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # Get available months and years from user's budget entries
    entries = (
        db.query(BudgetEntry.month, BudgetEntry.year)
        .filter(BudgetEntry.user_id == current_user.id)
        .distinct()
        .order_by(BudgetEntry.year.desc(), BudgetEntry.month)
        .all()
    )

    available_periods = []
    for month, year in entries:
        available_periods.append(
            {"month": month, "year": year, "display": f"{month} {year}"}
        )

    # Default to current month/year if no data exists
    if not available_periods:
        current_date = datetime.now()
        available_periods = [
            {
                "month": current_date.strftime("%B"),
                "year": current_date.year,
                "display": f"{current_date.strftime('%B')} {current_date.year}",
            }
        ]

    return templates.TemplateResponse(
        "monthly_analysis.html",
        {
            "request": request,
            "user": current_user,
            "available_periods": available_periods,
        },
    )


@app.get("/api/monthly-analysis-data/{year}/{month}")
async def get_monthly_analysis_data(
    year: int, month: str, request: Request, db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get the specific month's entry
    entry = (
        db.query(BudgetEntry)
        .filter(
            BudgetEntry.user_id == current_user.id,
            BudgetEntry.year == year,
            BudgetEntry.month == month,
        )
        .first()
    )

    if not entry:
        return {"error": "No data found for the specified month"}

    # Get previous month's data for comparison
    month_order = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    current_month_index = month_order.index(month)
    if current_month_index == 0:
        prev_month = "December"
        prev_year = year - 1
    else:
        prev_month = month_order[current_month_index - 1]
        prev_year = year

    prev_entry = (
        db.query(BudgetEntry)
        .filter(
            BudgetEntry.user_id == current_user.id,
            BudgetEntry.year == prev_year,
            BudgetEntry.month == prev_month,
        )
        .first()
    )

    # Calculate current month totals
    current_income = entry.salary + entry.freelancing_one + entry.freelancing_two
    current_expenses = (
        entry.mobile_recharge
        + entry.wifi
        + entry.emi_one
        + entry.emi_two
        + entry.emi_three
        + entry.emi_four
        + entry.food
        + entry.rent
        + entry.creditcard_one
        + entry.creditcard_two
        + entry.shopping
        + entry.travel
        + entry.other_expenses
    )
    # Calculate actual investments (only SIP, FD, ETF)
    current_investments = (
        entry.sip + entry.fixed_deposit_one + entry.fixed_deposit_two + entry.etf
    )
    # Calculate budget balance (remaining after expenses and investments)
    current_budget_balance = current_income - current_expenses - current_investments

    # Calculate previous month totals if available
    prev_income = prev_expenses = prev_investments = prev_budget_balance = 0
    if prev_entry:
        prev_income = (
            prev_entry.salary + prev_entry.freelancing_one + prev_entry.freelancing_two
        )
        prev_expenses = (
            prev_entry.mobile_recharge
            + prev_entry.wifi
            + prev_entry.emi_one
            + prev_entry.emi_two
            + prev_entry.emi_three
            + prev_entry.emi_four
            + prev_entry.food
            + prev_entry.rent
            + prev_entry.creditcard_one
            + prev_entry.creditcard_two
            + prev_entry.shopping
            + prev_entry.travel
            + prev_entry.other_expenses
        )
        prev_investments = (
            prev_entry.sip
            + prev_entry.fixed_deposit_one
            + prev_entry.fixed_deposit_two
            + prev_entry.etf
        )
        prev_budget_balance = prev_income - prev_expenses - prev_investments

    # Get year-to-date data for context
    ytd_entries = (
        db.query(BudgetEntry)
        .filter(BudgetEntry.user_id == current_user.id, BudgetEntry.year == year)
        .all()
    )

    ytd_income = sum(
        e.salary + e.freelancing_one + e.freelancing_two for e in ytd_entries
    )
    ytd_expenses = sum(
        e.mobile_recharge
        + e.wifi
        + e.emi_one
        + e.emi_two
        + e.emi_three
        + e.emi_four
        + e.food
        + e.rent
        + e.creditcard_one
        + e.creditcard_two
        + e.shopping
        + e.travel
        + e.other_expenses
        for e in ytd_entries
    )
    ytd_investments = sum(
        e.sip + e.fixed_deposit_one + e.fixed_deposit_two + e.etf for e in ytd_entries
    )
    ytd_budget_balance = ytd_income - ytd_expenses - ytd_investments

    monthly_data = {
        "month": month,
        "year": year,
        "current": {
            "income": {
                "salary": entry.salary,
                "freelancing_one": entry.freelancing_one,
                "freelancing_two": entry.freelancing_two,
                "total": current_income,
            },
            "expenses": {
                "mobile_recharge": entry.mobile_recharge,
                "wifi": entry.wifi,
                "emi_one": entry.emi_one,
                "emi_two": entry.emi_two,
                "emi_three": entry.emi_three,
                "emi_four": entry.emi_four,
                "food": entry.food,
                "rent": entry.rent,
                "creditcard_one": entry.creditcard_one,
                "creditcard_two": entry.creditcard_two,
                "shopping": entry.shopping,
                "travel": entry.travel,
                "other_expenses": entry.other_expenses,
                "total": current_expenses,
                "emi_total": entry.emi_one
                + entry.emi_two
                + entry.emi_three
                + entry.emi_four,
                "creditcard_total": entry.creditcard_one + entry.creditcard_two,
                "utilities_total": entry.mobile_recharge + entry.wifi,
            },
            "investments": {
                "sip": entry.sip,
                "fixed_deposit_one": entry.fixed_deposit_one,
                "fixed_deposit_two": entry.fixed_deposit_two,
                "etf": entry.etf,
                "total": current_investments,
            },
            "budget_balance": current_budget_balance,
        },
        "previous": {
            "month": prev_month,
            "year": prev_year,
            "income": prev_income,
            "expenses": prev_expenses,
            "investments": prev_investments,
            "budget_balance": prev_budget_balance,
            "has_data": prev_entry is not None,
        },
        "year_to_date": {
            "income": ytd_income,
            "expenses": ytd_expenses,
            "investments": ytd_investments,
            "budget_balance": ytd_budget_balance,
            "months_count": len(ytd_entries),
            "avg_monthly_income": ytd_income / max(len(ytd_entries), 1),
            "avg_monthly_expenses": ytd_expenses / max(len(ytd_entries), 1),
            "avg_monthly_investments": ytd_investments / max(len(ytd_entries), 1),
        },
        "comparisons": {
            "income_change": current_income - prev_income if prev_entry else 0,
            "income_change_percent": (
                ((current_income - prev_income) / prev_income * 100)
                if prev_entry and prev_income > 0
                else 0
            ),
            "expenses_change": current_expenses - prev_expenses if prev_entry else 0,
            "expenses_change_percent": (
                ((current_expenses - prev_expenses) / prev_expenses * 100)
                if prev_entry and prev_expenses > 0
                else 0
            ),
            "investments_change": (
                current_investments - prev_investments if prev_entry else 0
            ),
            "investments_change_percent": (
                ((current_investments - prev_investments) / prev_investments * 100)
                if prev_entry and prev_investments != 0
                else 0
            ),
            "budget_balance_change": (
                current_budget_balance - prev_budget_balance if prev_entry else 0
            ),
        },
        "analytics": {
            "expense_to_income_ratio": (
                (current_expenses / current_income * 100) if current_income > 0 else 0
            ),
            "investment_rate": (
                (current_investments / current_income * 100)
                if current_income > 0
                else 0
            ),
            "largest_expense_category": max(
                [
                    ("Rent", entry.rent),
                    ("Food", entry.food),
                    (
                        "EMIs",
                        entry.emi_one
                        + entry.emi_two
                        + entry.emi_three
                        + entry.emi_four,
                    ),
                    ("Credit Cards", entry.creditcard_one + entry.creditcard_two),
                    ("Shopping", entry.shopping),
                    ("Travel", entry.travel),
                    ("Other", entry.other_expenses),
                ],
                key=lambda x: x[1],
            ),
        },
    }

    return monthly_data


# Data Export Routes (CSV/Excel Downloads)
@app.get("/export/budget", response_class=HTMLResponse)
async def export_page(request: Request, current_user: User = Depends(get_current_user)):
    """Data export page"""
    return templates.TemplateResponse(
        "export_data.html", {"request": request, "user": current_user}
    )


@app.get("/download/budget")
async def download_budget_data(
    format: str = "csv",
    month: str = None,
    year: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download budget data in CSV or Excel format"""
    try:
        import pandas as pd
        from fastapi.responses import StreamingResponse
        import io

        # Build query
        query = db.query(BudgetEntry).filter(BudgetEntry.user_id == current_user.id)

        if month and year:
            query = query.filter(BudgetEntry.month == month, BudgetEntry.year == year)
        elif year:
            query = query.filter(BudgetEntry.year == year)

        entries = query.all()

        if not entries:
            raise HTTPException(
                status_code=404, detail="No data found for the specified criteria"
            )

        # Prepare data for export
        data = []
        for entry in entries:
            total_income = entry.salary + entry.freelancing_one + entry.freelancing_two
            total_expenses = (
                entry.mobile_recharge
                + entry.wifi
                + entry.food
                + entry.rent
                + entry.emi_one
                + entry.emi_two
                + entry.emi_three
                + entry.emi_four
                + entry.creditcard_one
                + entry.creditcard_two
                + entry.shopping
                + entry.travel
                + entry.other_expenses
            )
            net_savings = total_income - total_expenses

            data.append(
                {
                    "Month": entry.month,
                    "Year": entry.year,
                    "Salary": entry.salary,
                    "Freelancing_1": entry.freelancing_one,
                    "Freelancing_2": entry.freelancing_two,
                    "Mobile_Recharge": entry.mobile_recharge,
                    "WiFi": entry.wifi,
                    "Food": entry.food,
                    "Rent": entry.rent,
                    "EMI_1": entry.emi_one,
                    "EMI_2": entry.emi_two,
                    "EMI_3": entry.emi_three,
                    "EMI_4": entry.emi_four,
                    "Credit_Card_1": entry.creditcard_one,
                    "Credit_Card_2": entry.creditcard_two,
                    "Shopping": entry.shopping,
                    "Travel": entry.travel,
                    "Other_Expenses": entry.other_expenses,
                    "Total_Income": total_income,
                    "Total_Expenses": total_expenses,
                    "Net_Savings": net_savings,
                    "Created_At": (
                        entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if entry.created_at
                        else ""
                    ),
                }
            )

        df = pd.DataFrame(data)

        # Generate filename
        if month and year:
            filename = f"budget_data_{month}_{year}"
        elif year:
            filename = f"budget_data_{year}"
        else:
            filename = "budget_data_all"

        # Export based on format
        if format.lower() == "excel":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Budget Data", index=False)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.read()),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}.xlsx"
                },
            )
        else:  # CSV format
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode("utf-8")),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
            )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Pandas not installed. Please install with: pip install pandas openpyxl",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/download/bucket-list")
async def download_bucket_list(
    format: str = "csv",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download bucket list data in CSV or Excel format"""
    try:
        import pandas as pd
        from fastapi.responses import StreamingResponse
        import io

        # Get bucket list items
        items = db.query(BucketList).filter(BucketList.user_id == current_user.id).all()

        if not items:
            raise HTTPException(status_code=404, detail="No bucket list items found")

        # Prepare data for export
        data = []
        for item in items:
            data.append(
                {
                    "Name": item.name,
                    "Category": item.category,
                    "Description": item.description or "",
                    "Price": item.price,
                    "Priority": item.priority or "",
                    "Status": item.status or "Pending",
                    "Target_Date": (
                        item.target_date.strftime("%Y-%m-%d")
                        if item.target_date
                        else ""
                    ),
                    "Notes": item.notes or "",
                    "Created_At": (
                        item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if item.created_at
                        else ""
                    ),
                    "Updated_At": (
                        item.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                        if item.updated_at
                        else ""
                    ),
                }
            )

        df = pd.DataFrame(data)
        filename = "bucket_list_data"

        # Export based on format
        if format.lower() == "excel":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Bucket List", index=False)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.read()),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}.xlsx"
                },
            )
        else:  # CSV format
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode("utf-8")),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
            )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Pandas not installed. Please install with: pip install pandas openpyxl",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/download/variable-expenses")
async def download_variable_expenses(
    format: str = "csv",
    month: str = None,
    year: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download variable expenses data in CSV or Excel format"""
    try:
        import pandas as pd
        from fastapi.responses import StreamingResponse
        import io

        # Build query
        query = db.query(VariableBudgetEntry).filter(
            VariableBudgetEntry.user_id == current_user.id
        )

        if month and year:
            query = query.filter(
                VariableBudgetEntry.month == month, VariableBudgetEntry.year == year
            )
        elif year:
            query = query.filter(VariableBudgetEntry.year == year)

        expenses = query.all()

        if not expenses:
            raise HTTPException(
                status_code=404,
                detail="No variable expenses found for the specified criteria",
            )

        # Prepare data for export
        data = []
        for expense in expenses:
            data.append(
                {
                    "Month": expense.month,
                    "Year": expense.year,
                    "Description": expense.description,
                    "Amount": expense.amount,
                    "Category": expense.category,
                    "Date_Added": (
                        expense.date_added.strftime("%Y-%m-%d %H:%M:%S")
                        if expense.date_added
                        else ""
                    ),
                    "Is_Finalized": expense.is_finalized,
                }
            )

        df = pd.DataFrame(data)

        # Generate filename
        if month and year:
            filename = f"variable_expenses_{month}_{year}"
        elif year:
            filename = f"variable_expenses_{year}"
        else:
            filename = "variable_expenses_all"

        # Export based on format
        if format.lower() == "excel":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Variable Expenses", index=False)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.read()),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}.xlsx"
                },
            )
        else:  # CSV format
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode("utf-8")),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
            )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Pandas not installed. Please install with: pip install pandas openpyxl",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # Use environment variables for port and host
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(app, host=host, port=port)
