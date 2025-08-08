import os
from dotenv import load_dotenv

load_dotenv()

# Ringba webhook filters
RINGBA_FILTERS = {
    "campaign_name": os.getenv("RINGBA_CAMPAIGN_NAME", "Your Campaign Name"),
    "target_name": os.getenv("RINGBA_TARGET_NAME", "Your Target Name")
}

# Google Sheets configuration
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "your_google_sheet_id_here")
GOOGLE_SHEET_TAB = os.getenv("GOOGLE_SHEET_TAB", "Sheet1")
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE", "credentials.json")

# Slack configuration
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/XXXX/YYYY/ZZZZ")

# Flask configuration for local server
FLASK_ENV = os.getenv("FLASK_ENV", "production")  # Changed to production for server
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"  # Changed to False for server
HOST = os.getenv("HOST", "0.0.0.0")  # Allow external connections
PORT = int(os.getenv("PORT", 5000))
