import sys
import os

# Add your project directory to Python path
path = "/home/veera7474/budget-palnner"  # Replace 'yourusername' with your actual PythonAnywhere username
if path not in sys.path:
    sys.path.insert(0, path)

# Activate virtual environment
activate_this = (
    "/home/veera7474/budget-palnner/venv/bin/activate_this.py"  # Replace 'yourusername'
)
try:
    with open(activate_this) as file_:
        exec(file_.read(), dict(__file__=activate_this))
except FileNotFoundError:
    pass

# Set environment variables
os.environ["SECRET_KEY"] = "your-production-secret-key-here"
os.environ["REFRESH_SECRET_KEY"] = "your-production-refresh-secret-key-here"
os.environ["DATABASE_URL"] = (
    "sqlite:////home/veera7474/budget-palnner/budget.db"  # Replace 'yourusername'
)

# Import your FastAPI app
from main import app

# WSGI application
application = app
