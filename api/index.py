import sys
from pathlib import Path

# Add project root to path so we can import from web directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the Flask app from web/app.py
from web.app import app

# For direct import compatibility
if __name__ == "__main__":
    app.run()