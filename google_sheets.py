import datetime
import gspread
import json
import os
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, GOOGLE_SHEET_TAB, GOOGLE_CREDS_FILE
import logging

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def append_row_to_sheet(time_of_call, caller_id, call_type=""):
    try:
        # Try to get credentials from environment variable first (for deployment)
        creds_json = os.getenv('GOOGLE_CREDS_JSON')
        if creds_json:
            creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
        else:
            # Fall back to file-based credentials (for local development)
            creds = Credentials.from_service_account_file(GOOGLE_CREDS_FILE, scopes=SCOPES)
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(GOOGLE_SHEET_TAB)
        
        # Define correct headers - now including Call Type
        correct_headers = ["Time of call", "CallerID", "Call Type", "Agent Name", "Status", "Notes"]
        
        # Check if headers exist and are correct
        try:
            existing_headers = sheet.row_values(1)
            if not existing_headers or existing_headers != correct_headers:
                # Clear the sheet and add correct headers
                sheet.clear()
                sheet.append_row(correct_headers)
                logging.info("Created correct headers in Google Sheet")
        except Exception as e:
            # If there's an error reading headers, clear and create new ones
            sheet.clear()
            sheet.append_row(correct_headers)
            logging.info("Created correct headers in Google Sheet (after error)")
        
        # Find next empty row by checking ONLY Column A (ignore formulas in other columns)
        col_a_values = sheet.col_values(1)  # Get only Column A values
        next_row = len([val for val in col_a_values if val]) + 1
        
        # Explicitly write to specific columns - this bypasses append_row() confusion
        sheet.update(f'A{next_row}', time_of_call)
        sheet.update(f'B{next_row}', caller_id)
        sheet.update(f'C{next_row}', call_type)
        sheet.update(f'D{next_row}', "")  # Agent Name
        sheet.update(f'E{next_row}', "")  # Status
        sheet.update(f'F{next_row}', "")  # Notes
        
        logging.info(f"Successfully appended row {next_row} for caller {caller_id} with call type {call_type}")
        return True
        
    except Exception as e:
        logging.error(f"Error appending to Google Sheet: {str(e)}")
        return False
